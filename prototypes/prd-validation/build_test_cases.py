#!/usr/bin/env python3
"""从 testing_ir.json 注入 endpoint 字符串，生成 test_cases.json。"""
import json

ir = json.load(open("testing_ir.json", encoding="utf-8"))
EP = {c["contract_id"]: c["endpoint"] for c in ir["interface_contracts"]}

def case(case_id, req, rule, scenario, fixture, steps, expected,
         sm=None, constraint_refs=None, entity=None):
    c = {
        "case_id": case_id,
        "req_id": req,
        "rule_id": rule,
        "scenario_id": scenario,
        "fixture_category": fixture,
        "steps": steps,
        "expected_results": expected,
    }
    if sm:
        c["state_machine_id"] = sm
    if entity:
        c["entity_id"] = entity
    if constraint_refs:
        c["constraint_refs"] = constraint_refs
    return c

cases = [
    # ---- 上报包处理状态机（SM-001）----
    case("TC-PKG-001", "REQ-003", "BR-001", "S-PKG-001", "Dynamic",
         [{"action": "月度任务生成后，机构上传合法enc上报包，等待采集处理"}],
         [{"state": "正在处理",
           "assertion": "上报包状态由 等待处理 流转为 正在处理，解密节点记录毫秒级时间戳"}],
         sm="SM-001"),
    case("TC-PKG-002", "REQ-003", "BR-002", "S-PKG-002", "Dynamic",
         [{"action": "上传非删除类上报包，解密/解压/校验全部通过"}],
         [{"state": "处理完毕无反馈",
           "assertion": "状态流转为 处理完毕无反馈，不生成反馈文件"}],
         sm="SM-001"),
    case("TC-PKG-003", "REQ-003", "BR-002", "S-PKG-003", "Dynamic",
         [{"action": "上传校验必败的上报包（解密失败样本）"}],
         [{"state": "处理完毕有反馈",
           "assertion": "状态流转为 处理完毕有反馈，生成反馈文件且失败节点时间戳非空"}],
         sm="SM-001"),
    case("TC-PKG-004", "REQ-003", "BR-002", "S-PKG-004", "Dynamic",
         [{"action": "注入处理过程异常（解压服务不可用）后上传上报包"}],
         [{"state": "处理异常",
           "assertion": "状态流转为 处理异常，异常信息可在上报详情列表查看"}],
         sm="SM-001"),
    case("TC-PKG-005", "REQ-003", "BR-001", "S-PKG-005", "Dynamic",
         [{"action": "对 处理异常 的上报包执行重新采集"}],
         [{"state": "等待处理",
           "assertion": "状态回到 等待处理，续跑起点为原失败节点而非从头处理"}],
         sm="SM-001"),
    # ---- 删除审批状态机（SM-002）----
    case("TC-APR-001", "REQ-004", "BR-002", "S-APR-001", "Static",
         [{"action": "对成功数量不为0的删除类数据包发起删除审批并选择通过"}],
         [{"state": "审批通过",
           "assertion": "审批记录状态为 审批通过，生成待次日定时删除的数据清单"}],
         sm="SM-002"),
    case("TC-APR-002", "REQ-004", "BR-002", "S-APR-002", "Static",
         [{"action": "对删除类数据包发起审批并选择不通过，填写备注"}],
         [{"state": "审批不通过",
           "assertion": "审批记录状态为 审批不通过，备注内容与填写值一致，数据保留"}],
         sm="SM-002"),
    # ---- 查询启停状态机（SM-003）----
    case("TC-QRY-001", "REQ-007", "BR-003", "S-QRY-001", "Dynamic",
         [{"action": "构造签约机构调用量超过最大调用量，等待次日12:00定时任务"}],
         [{"state": "停用",
           "assertion": "次日12:00后查询状态为 停用，该机构查询请求被拒绝"}],
         sm="SM-003"),
    case("TC-QRY-002", "REQ-006", "BR-003", "S-QRY-002", "Dynamic",
         [{"action": "对已停用且已用量小于最大调用量的机构执行手动启用"}],
         [{"state": "启用",
           "assertion": "查询状态恢复为 启用，查询服务立即可用"}],
         sm="SM-003"),
    # ---- 上传校验 ----
    case("TC-UPLOAD-001", "REQ-001", "BR-001", "S-UPLOAD-001", "Static",
         [{"action": "上传27位包名满足全部11项规则、大小10M的enc包"}],
         [{"assertion": "上传成功，包进入 等待处理 队列，无校验提示"}]),
    case("TC-UPLOAD-002", "REQ-001", "BR-001", "S-UPLOAD-002", "Static",
         [{"action": "上传组织机构代码位非法的27位包名enc包"}],
         [{"assertion": "实时校验拦截上传，页面提示第5位组织机构代码错误（裁决口径）"}]),
    case("TC-UPLOAD-003", "REQ-001", "BR-001", "S-UPLOAD-003", "Static",
         [{"action": "上传大小为51M的enc包"}],
         [{"assertion": "上传被拒绝，提示文件大小超过50M限制"}],
         constraint_refs=["CON-002"]),
    case("TC-UPLOAD-004", "REQ-001", "BR-001", "S-UPLOAD-004", "Static",
         [{"action": "上传包名日期位为19900101的enc包"}],
         [{"assertion": "上传成功：日期不早于1990年（含）边界按通过处理（裁决口径）"}]),
    case("TC-UPLOAD-005", "REQ-001", "BR-001", "S-UPLOAD-005", "Static",
         [{"action": "上传大小恰为50M的enc包"}],
         [{"assertion": "上传成功：文件大小<=50M 含边界"}],
         constraint_refs=["CON-002"]),
    # ---- 任务/删除/查询 ----
    case("TC-TASK-001", "REQ-002", "BR-001", "S-TASK-001", "Dynamic",
         [{"action": "将系统时间推进至每月1号凌晨，触发上报任务生成定时任务"}],
         [{"assertion": "仅为启用状态的接入机构生成本月上报任务，上报月份=当前月，停用机构无任务"}]),
    case("TC-DEL-001", "REQ-005", "BR-002", "S-DEL-001", "Dynamic",
         [{"action": "删除审批通过后，将系统时间推进至次日定时任务执行点"}],
         [{"assertion": "审批通过的数据被自动删除，未审批数据保留"}]),
    case("TC-DEL-002", "REQ-004", "BR-002", "S-DEL-002", "Static",
         [{"action": "上传类型为删除且成功数量为0的数据包"}],
         [{"assertion": "不生成删除审批记录（裁决口径B：删除且成功数量不为0才触发）"}]),
    case("TC-QRY-003", "REQ-008", "BR-004", "S-QRY-003", "Dynamic",
         [{"action": "机构用户发起一次产品查询"}],
         [{"assertion": "查询记录新增1条，且该机构检索次数计数加1"}]),
    case("TC-QRY-004", "REQ-007", "BR-003", "S-QRY-004", "Dynamic",
         [{"action": "机构调用量超额后、次日12:00停用执行前提升其配额至用量之上"}],
         [{"assertion": "次日12:00不触发停用，查询状态保持 启用"}]),
    case("TC-QRY-005", "REQ-007", "BR-003", "S-QRY-005", "Dynamic",
         [{"action": "构造机构调用量恰等于最大调用量"}],
         [{"assertion": "不判定为超额，次日12:00不触发停用"}]),
    case("TC-QRY-006", "REQ-008", "BR-004", "S-QRY-006", "Static",
         [{"action": "在查询明细页按最近1年时间范围查询，命中记录超过200条"}],
         [{"assertion": "返回记录数为200条（上限），超出部分不返回"}],
         constraint_refs=["CON-003"]),
    case("TC-EXPORT-001", "REQ-008", "BR-004", "S-QRY-003", "Dynamic",
         [{"action": "构造50001条查询记录后执行列表导出"}],
         [{"assertion": "单次导出记录数为50000条（上限），并提示超出部分需分批导出"}],
         constraint_refs=["CON-001"]),
    # ---- 系数与费用单 ----
    case("TC-COEF-001", "REQ-010", "BR-005", "S-COEF-001", "Dynamic",
         [{"action": "将系统时间推进至每月1日凌晨，触发月度调节系数生成"}],
         [{"assertion": "按结算协议机构数量生成上月月度调节系数，无协议机构不生成"}]),
    case("TC-COEF-002", "REQ-010", "BR-006", "S-COEF-002", "Static",
         [{"action": "对按笔结算机构，取X=0.8、Y=0.9、Z=1.0执行调节系数积计算"}],
         [{"assertion": "调节系数积=0.8×0.9×1.0=0.72"}]),
    case("TC-COEF-003", "REQ-009", "BR-006", "S-COEF-003", "Static",
         [{"action": "按系数说明表逐行核对X/Y/Z映射取值（映射规则仅原型图，待澄清项）"}],
         [{"assertion": "X/Y/Z取值与系数说明表一致；不一致项记录为待澄清缺陷并提交产品确认"}]),
    case("TC-BILL-001", "REQ-011", "BR-007", "S-BILL-001", "Static",
         [{"action": "构造有效调用量1000、会员免费调用量200的机构生成费用单"}],
         [{"assertion": "结算调用量=1000-200=800"}]),
    case("TC-BILL-002", "REQ-011", "BR-008", "S-BILL-002", "Static",
         [{"action": "构造包月机构：有效调用量1000、包月调用量600、会员免费调用量100"}],
         [{"assertion": "包月套餐外调用量=1000-600-100=300"}]),
    case("TC-BILL-003", "REQ-012", "BR-009", "S-BILL-003", "Dynamic",
         [{"action": "M-1月已有费用单数据时点击生成费用单"}],
         [{"assertion": "M-1月调节系数积与费用单明细先被删除，再按当前数据重建，费用单总额与重算值一致"}],
         constraint_refs=["CON-005"]),
    case("TC-BILL-004", "REQ-012", "BR-009", "S-BILL-004", "Dynamic",
         [{"action": "在生成费用单的删除阶段后注入失败（重建中断）"}],
         [{"assertion": "记录M-1月数据实际状态；因PRD未定义回滚，结果标记为待产品确认的缺口证据"}]),
    # ---- 权限 ----
    case("TC-PERM-001", "REQ-008", "BR-004", "S-PERM-001", "Static",
         [{"action": "协会用户发起一次产品查询"}],
         [{"assertion": "查询记录新增1条，检索次数计数保持不变"}]),
    case("TC-APR-003", "REQ-004", "BR-002", "S-APR-003", "Static",
         [{"action": "以无审批权限的普通用户账号尝试操作删除审批"}],
         [{"assertion": "审批操作入口不可用或操作被拒绝；权限矩阵待《角色权限表》补充后细化"}]),
    # ---- 性能占位（CON-004，Out_Of_Scope 登记）----
    case("TC-PERF-001", "REQ-007", "BR-003", "S-QRY-001", "Dynamic",
         [{"action": "性能专项占位：按CON-004指标执行压测（本轮范围外，仅登记约束）"}],
         [{"assertion": "占位用例：峰值>=6000笔/秒、平均响应<=500ms、成功率>=99.9% 由性能测试计划承接"}],
         constraint_refs=["CON-004"]),
]

# ---- 接口契约覆盖（IC-001~IC-005，endpoint 从 IR 注入）----
api_bindings = [
    ("TC-API-001", "IC-001", "REQ-003", "BR-001", "S-PKG-001",
     "通过接口明细数据上报通道上报数据包，响应受理成功"),
    ("TC-API-002", "IC-002", "REQ-003", "BR-002", "S-PKG-002",
     "通过接口查询上报情况，返回包处理状态与网页端一致"),
    ("TC-API-003", "IC-003", "REQ-014", "BR-004", "S-API-001",
     "通过接口发起信贷交易信息查询，响应参数与网页端一致"),
    ("TC-API-004", "IC-004", "REQ-008", "BR-004", "S-QRY-003",
     "通过检索次数接口核对机构检索次数扣减结果"),
    ("TC-API-005", "IC-005", "REQ-014", "BR-004", "S-API-002",
     "调用升级产品接口（国密算法），验签与响应字段计算同网页端"),
]
for case_id, cid, req, rule, scenario, intent in api_bindings:
    cases.append(case(
        case_id, req, rule, scenario, "Dynamic",
        [{"action": intent, "endpoint": EP[cid], "method": "POST"}],
        [{"assertion": f"接口返回受理成功（{cid} 契约占位：PRD未提供接口文档，字段级断言待补文档后细化）"}],
    ))

with open("test_cases.json", "w", encoding="utf-8") as fh:
    json.dump({"cases": cases}, fh, ensure_ascii=False, indent=2)
print(f"cases={len(cases)}")
