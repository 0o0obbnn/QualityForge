"""起草 Testing IR（v1.0），产出两个版本：

- testing_ir_unresolved.json：4 处冲突保留双版本但未裁决 → 预期 ir-validator REJECT
- testing_ir.json：模拟人工裁决（HITL）后的发布版 → 预期 PASS

裁决说明：PRD 的真实矛盾在评审阶段已上报（Q-003/Q-005/Q-006），本文件中的
resolution 是为验证下游链路而做的*模拟*裁决，逐条标注"测试裁决"，不代表
产品结论。
"""
import copy
import json

PRD = "PRD-V2-20260811"

requirements = [
    {"req_id": "REQ-001", "title": "enc包名校验（27位结构11项规则）",
     "description": "上传enc包时按11项规则校验27位包名与50M大小；实时校验与toast提示两套口径矛盾（1~9位是否含法人标识代码、1990边界含不含）",
     "validation_status": "NEED_HUMAN_REVIEW",
     "source_trace": f"{PRD}§1.2.1:L323-L359", "confidence": 0.85,
     "conflict": True,
     "conflict_refs": [f"{PRD}§1.2.1:实时校验规则⑤⑦（L323,L327）",
                        f"{PRD}§1.2.1:toast错误提示⑤⑦（L347,L351）"],
     "resolution": "测试裁决（模拟HITL）：采用实时校验口径并保留待产品确认；1~9位仅组织机构代码、日期不早于1990年（含）"},
    {"req_id": "REQ-002", "title": "每月1号自动生成上报任务",
     "description": "每月1号凌晨系统自动生成本月上报任务，机构范围为启用状态的接入机构；接口上报月份只能是当前月",
     "validation_status": "PENDING",
     "source_trace": f"{PRD}§1.2.1:L135-L141", "confidence": 0.88},
    {"req_id": "REQ-003", "title": "上报包处理状态机",
     "description": "上报包处理状态：等待处理/正在处理/处理完毕无反馈/处理完毕有反馈/处理异常；解密→解压→校验各节点记录毫秒级时间戳",
     "validation_status": "PENDING",
     "source_trace": f"{PRD}§1.2.2:L432,L624-L627", "confidence": 0.86},
    {"req_id": "REQ-004", "title": "删除审批触发条件",
     "description": "删除类数据包需删除审批；触发条件两种口径（类型为删除即审批 vs 删除且成功数量不为0）",
     "validation_status": "NEED_HUMAN_REVIEW",
     "source_trace": f"{PRD}§1.2.2:L520,L654", "confidence": 0.8,
     "conflict": True,
     "conflict_refs": [f"{PRD}§1.2.2:上报详情列表（L520）",
                        f"{PRD}§1.2.2:查看弹窗（L654）"],
     "resolution": "测试裁决（模拟HITL）：采用'删除且成功数量不为0'口径（出现两处，频次占优），保留待产品确认"},
    {"req_id": "REQ-005", "title": "删除定时任务",
     "description": "审批通过后系统于次日定时任务自动删除数据；未审批或审批不通过数据保留",
     "validation_status": "PENDING",
     "source_trace": f"{PRD}§1.5.1:L1511", "confidence": 0.92},
    {"req_id": "REQ-006", "title": "查询状态启停规则",
     "description": "查询状态启停矛盾口径：业务规则称当前月份可停用/启用 vs 字段描述称只能手动启用不可手工停用",
     "validation_status": "NEED_HUMAN_REVIEW",
     "source_trace": f"{PRD}§1.6:L1775,L1873", "confidence": 0.8,
     "conflict": True,
     "conflict_refs": [f"{PRD}§1.6:业务规则（L1775,L2015）",
                        f"{PRD}§1.6:查询状态字段描述（L1873）"],
     "resolution": "测试裁决（模拟HITL）：采用'只能手动启用、停用由系统自动执行'口径（与自动停用规则自洽），保留待产品确认"},
    {"req_id": "REQ-007", "title": "查询超额自动停用",
     "description": "签约/未签约/试用机构调用量超额后，系统于次日中午12:00自动停止查询服务；停用前提升配额则不停用",
     "validation_status": "PENDING",
     "source_trace": f"{PRD}§1.6:L1771,L2011,L2264", "confidence": 0.9},
    {"req_id": "REQ-008", "title": "查询与检索次数记录",
     "description": "机构用户查询记录查询记录与检索次数，检索次数耗完停用时提示；协会用户仅记录查询记录不记录检索次数",
     "validation_status": "PENDING",
     "source_trace": f"{PRD}§1.4.1:L1087-L1089", "confidence": 0.91},
    {"req_id": "REQ-009", "title": "系数XYZ计算",
     "description": "数据贡献量系数X/调用量系数Y/质量系数Z按系数说明表映射并每日汇总更新；系数映射规则仅有原型图无文字定义",
     "validation_status": "NEED_HUMAN_REVIEW",
     "source_trace": f"{PRD}§1.9.1:L2967,L3103,L3230", "confidence": 0.6},
    {"req_id": "REQ-010", "title": "调节系数积生成",
     "description": "每月1日凌晨按结算协议机构数量生成上月月度调节系数；按笔结算=XYZ三系数相乘，包月结算=XZ相乘",
     "validation_status": "PENDING",
     "source_trace": f"{PRD}§1.9.2:L3392,L3501", "confidence": 0.82},
    {"req_id": "REQ-011", "title": "费用单费用公式",
     "description": "结算调用量=有效调用量-会员免费调用量；包月套餐外调用量=有效调用量-包月调用量-会员免费调用量",
     "validation_status": "PENDING",
     "source_trace": f"{PRD}§1.9.4:L4078,L4107", "confidence": 0.87},
    {"req_id": "REQ-012", "title": "生成费用单（先删后建）",
     "description": "生成费用单先删除调节系数积与费用单明细表中M-1月数据，再用M-1月现有数据重新生成；权限/确认/回滚未定义",
     "validation_status": "NEED_HUMAN_REVIEW",
     "source_trace": f"{PRD}§1.9.4:L4181", "confidence": 0.78},
    {"req_id": "REQ-013", "title": "角色权限控制",
     "description": "按《角色权限表》增加对应功能的角色权限；权限表未随文档提供，权限模型不可验收",
     "validation_status": "NEED_HUMAN_REVIEW",
     "source_trace": f"{PRD}§1.11.1:L4260", "confidence": 0.55},
    {"req_id": "REQ-014", "title": "接口端产品查询",
     "description": "基础/升级产品接口端响应参数与字段值计算逻辑同网页端一致；接口文档未提供",
     "validation_status": "NEED_HUMAN_REVIEW",
     "source_trace": f"{PRD}§1.4:L1182,L1501", "confidence": 0.65},
]

business_rules = [
    {"rule_id": "BR-001", "condition": "每月1号凌晨",
     "action": "为启用状态的接入机构生成本月上报任务",
     "source": PRD, "source_trace": f"{PRD}§1.2.1:L135,L137", "confidence": 0.88},
    {"rule_id": "BR-002", "condition": "上报数据包类型为删除（口径A）/类型为删除且成功数量不为0（口径B）",
     "action": "生成删除审批记录",
     "source": PRD, "source_trace": f"{PRD}§1.2.2:L520,L654", "confidence": 0.8,
     "conflict": True,
     "conflict_refs": [f"{PRD}§1.2.2:列表口径（L520）", f"{PRD}§1.2.2:弹窗口径（L654）"],
     "resolution": "测试裁决（模拟HITL）：同REQ-004，采用口径B"},
    {"rule_id": "BR-003", "condition": "调用量超过最大调用量（签约/未签约/试用各自判定）",
     "action": "次日中午12:00自动停止查询服务；停用前提升配额则不停用",
     "source": PRD, "source_trace": f"{PRD}§1.6:L1771,L2011,L2264", "confidence": 0.9},
    {"rule_id": "BR-004", "condition": "机构用户发起查询",
     "action": "记录查询记录与检索次数；协会用户仅记录查询记录",
     "source": PRD, "source_trace": f"{PRD}§1.4.1:L1087,L1089", "confidence": 0.91},
    {"rule_id": "BR-005", "condition": "每月1日凌晨",
     "action": "按结算协议机构数量生成上月月度调节系数",
     "source": PRD, "source_trace": f"{PRD}§1.9.2:L3392", "confidence": 0.85},
    {"rule_id": "BR-006", "condition": "结算模式=按笔结算",
     "action": "调节系数积=数据贡献量系数x数据调用量系数x数据质量系数",
     "source": PRD, "source_trace": f"{PRD}§1.9.2:L3501", "confidence": 0.85},
    {"rule_id": "BR-007", "condition": "费用单生成",
     "action": "结算调用量=有效调用量-会员免费调用量",
     "source": PRD, "source_trace": f"{PRD}§1.9.4:L4078", "confidence": 0.87},
    {"rule_id": "BR-008", "condition": "结算模式=包月结算",
     "action": "包月套餐外调用量=有效调用量-包月调用量-会员免费调用量",
     "source": PRD, "source_trace": f"{PRD}§1.9.4:L4107", "confidence": 0.87},
    {"rule_id": "BR-009", "condition": "点击生成费用单",
     "action": "先删除M-1月调节系数积与费用单明细数据，再重新生成",
     "source": PRD, "source_trace": f"{PRD}§1.9.4:L4181", "confidence": 0.8},
    {"rule_id": "BR-010", "condition": "机构无结算协议且有试用机构标签",
     "action": "判定为试用机构；列表行手动新增",
     "source": PRD, "source_trace": f"{PRD}§1.6:L2264,L2266", "confidence": 0.89},
]

entities = [
    {"entity_id": "ENT-001", "name": "上报数据包", "fields": [
        {"name": "package_name", "sensitivity_level": "INTERNAL"},
        {"name": "org_code", "sensitivity_level": "INTERNAL"},
        {"name": "packet_type", "sensitivity_level": "INTERNAL"},
        {"name": "process_status", "sensitivity_level": "INTERNAL"},
        {"name": "success_count", "sensitivity_level": "INTERNAL"}]},
    {"entity_id": "ENT-002", "name": "删除审批记录", "fields": [
        {"name": "approval_status", "sensitivity_level": "INTERNAL"},
        {"name": "remark", "sensitivity_level": "INTERNAL"},
        {"name": "delete_count", "sensitivity_level": "INTERNAL"}]},
    {"entity_id": "ENT-003", "name": "检索次数记录", "fields": [
        {"name": "org_name", "sensitivity_level": "INTERNAL"},
        {"name": "query_status", "sensitivity_level": "INTERNAL"},
        {"name": "used_amount", "sensitivity_level": "INTERNAL"},
        {"name": "max_call_amount", "sensitivity_level": "INTERNAL"}]},
    {"entity_id": "ENT-004", "name": "结算协议", "fields": [
        {"name": "agreement_status", "sensitivity_level": "INTERNAL"},
        {"name": "billing_start_time", "sensitivity_level": "INTERNAL"},
        {"name": "billing_mode", "sensitivity_level": "INTERNAL"}]},
    {"entity_id": "ENT-005", "name": "机构", "fields": [
        {"name": "org_name", "sensitivity_level": "PUBLIC",
         "sensitivity_rationale": "接入机构名称为公开工商信息，文档列表页公开展示"},
        {"name": "social_credit_code", "sensitivity_level": "SENSITIVE"},
        {"name": "member_duty", "sensitivity_level": "INTERNAL"}]},
    {"entity_id": "ENT-006", "name": "费用单", "fields": [
        {"name": "billing_call_amount", "sensitivity_level": "INTERNAL"},
        {"name": "monthly_fee", "sensitivity_level": "SENSITIVE"}]},
    {"entity_id": "ENT-007", "name": "查询记录", "fields": [
        {"name": "customer_name", "sensitivity_level": "SENSITIVE"},
        {"name": "id_number", "sensitivity_level": "SENSITIVE"},
        {"name": "query_reason", "sensitivity_level": "INTERNAL"}]},
]

state_machines = [
    {"sm_id": "SM-001", "entity_id": "ENT-001", "initial_state": "等待处理",
     "states": ["等待处理", "正在处理", "处理完毕无反馈", "处理完毕有反馈", "处理异常"],
     "transitions": [
         {"from": "等待处理", "to": "正在处理", "guard": "采集成功开始处理"},
         {"from": "正在处理", "to": "处理完毕无反馈", "guard": "校验通过（非删除类或无需反馈）"},
         {"from": "正在处理", "to": "处理完毕有反馈", "guard": "解密/解压/校验失败，生成反馈文件"},
         {"from": "正在处理", "to": "处理异常", "guard": "处理过程异常"},
         {"from": "处理异常", "to": "等待处理", "guard": "重新采集，从失败节点续跑"}],
     "terminal_states": ["处理完毕无反馈", "处理完毕有反馈"]},
    {"sm_id": "SM-002", "entity_id": "ENT-002", "initial_state": "待审批",
     "states": ["待审批", "审批通过", "审批不通过"],
     "transitions": [
         {"from": "待审批", "to": "审批通过", "guard": "审批人通过"},
         {"from": "待审批", "to": "审批不通过", "guard": "审批人不通过（备注必填）"}],
     "terminal_states": ["审批通过", "审批不通过"]},
    {"sm_id": "SM-003", "entity_id": "ENT-003", "initial_state": "启用",
     "states": ["启用", "停用"],
     "transitions": [
         {"from": "启用", "to": "停用", "guard": "超额后次日12:00自动停用/试用周期结束"},
         {"from": "停用", "to": "启用", "guard": "手动启用且已用量<最大调用量"}],
     "terminal_states": {}},
]

interface_contracts = [
    {"contract_id": "IC-001", "endpoint": "未提供（历史接口：接口明细数据上报，PRD未给契约）", "method": "POST"},
    {"contract_id": "IC-002", "endpoint": "未提供（历史接口：接口明细上报情况查询）", "method": "POST"},
    {"contract_id": "IC-003", "endpoint": "未提供（历史接口：接口信贷交易信息查询）", "method": "POST"},
    {"contract_id": "IC-004", "endpoint": "未提供（历史接口：检索次数接口）", "method": "POST"},
    {"contract_id": "IC-005", "endpoint": "未提供（新增升级产品调用接口，国密算法，PRD未给设计）", "method": "POST"},
]

constraints = [
    {"constraint_id": "CON-001", "target": "列表导出", "expression": "每次最多导出50000条",
     "source_trace": f"{PRD}§1.2.1:L283"},
    {"constraint_id": "CON-002", "target": "enc文件包", "expression": "文件大小<=50M",
     "source_trace": f"{PRD}§1.2.1:L335"},
    {"constraint_id": "CON-003", "target": "查询明细", "expression": "最近1年查询记录，上限200条",
     "source_trace": f"{PRD}§1.4.1:L1165"},
    {"constraint_id": "CON-004", "target": "查询性能", "expression": "峰值>=6000笔/秒 且 平均响应<=500ms 且 成功率>=99.9%",
     "source_trace": f"{PRD}§2.1:L4311-L4315"},
    {"constraint_id": "CON-005", "target": "数据一致性", "expression": "100%（最终一致性）——语义互斥，列为待澄清约束",
     "source_trace": f"{PRD}§2.1:L4337"},
]

ir = {
    "ir_version": "1.0",
    "requirements": requirements,
    "business_rules": business_rules,
    "entities": entities,
    "state_machines": state_machines,
    "interface_contracts": interface_contracts,
    "constraints": constraints,
}

# 版本1：未裁决（移除 resolution_status，保留 conflict=true 与双版本）
unresolved = copy.deepcopy(ir)
for cls in ("requirements", "business_rules"):
    for item in unresolved[cls]:
        if item.get("conflict"):
            item.pop("resolution", None)
with open("testing_ir_unresolved.json", "w", encoding="utf-8") as fh:
    json.dump(unresolved, fh, ensure_ascii=False, indent=2)

# 版本2：模拟人工裁决后（conflict=true + resolution_status=RESOLVED + resolution 记录）
resolved = copy.deepcopy(ir)
for cls in ("requirements", "business_rules"):
    for item in resolved[cls]:
        if item.get("conflict"):
            item["resolution_status"] = "RESOLVED"
with open("testing_ir.json", "w", encoding="utf-8") as fh:
    json.dump(resolved, fh, ensure_ascii=False, indent=2)

print("written: testing_ir_unresolved.json（冲突未裁决）, testing_ir.json（模拟裁决后）")
