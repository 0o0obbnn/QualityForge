#!/usr/bin/env python3
"""Render dependency-free hierarchy, ER, and relationship views from one graph."""

from __future__ import annotations

import argparse
import html as html_module
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Render interactive requirement graph views")
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    data = json.loads(args.mapping.read_text(encoding="utf-8"))
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = html_module.escape(str(data.get("meta", {}).get("document", "功能点图谱")))
    args.out.write_text(TEMPLATE.replace("__TITLE__", title).replace("__DATA__", payload), encoding="utf-8")
    return 0


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ · 需求知识图谱</title><style>
:root{--bg:#f5f7fb;--ink:#172033;--muted:#667085;--line:#cbd3df;--fun:#175cd3;--atomic:#087443;--field:#8a3ffc;--object:#b54708;--state:#c11574;--danger:#b42318}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,-apple-system,"PingFang SC",sans-serif;color:var(--ink);background:var(--bg)}
header{padding:14px 20px;background:#fff;border-bottom:1px solid #e5e9f0;display:flex;gap:12px;align-items:center;flex-wrap:wrap}h1{font-size:18px;margin:0 12px 0 0}
input,select{padding:8px 10px;border:1px solid #cbd3df;border-radius:8px;background:#fff}.stats{color:var(--muted)}
.notice{padding:9px 20px;font-weight:650;border-bottom:1px solid}.notice.fail{color:#912018;background:#fff0ee}.notice.partial{color:#854a0e;background:#fff6df}.notice.pass{color:#05603a;background:#eaf8f0}
main{display:grid;grid-template-columns:minmax(760px,1fr) 380px;height:calc(100vh - 106px)}#canvas{overflow:auto;background-image:radial-gradient(#d8deea 1px,transparent 1px);background-size:20px 20px}
svg{display:block;min-width:1180px}.edge{stroke:var(--line);stroke-width:1.2;fill:none}.edge.cross{stroke:#e07941;stroke-dasharray:5 3}.edge.conflict{stroke:var(--danger);stroke-width:2}.node{cursor:pointer}.node rect{rx:9;stroke-width:1.4}.node text{fill:#fff;font-size:12px;pointer-events:none}
.node.fun rect{fill:var(--fun)}.node.atomic rect{fill:var(--atomic)}.node.field rect{fill:var(--field)}.node.object rect{fill:var(--object)}.node.state rect{fill:var(--state)}.node.dim{opacity:.12}
aside{border-left:1px solid #dfe4ec;background:#fff;padding:18px;overflow:auto}aside h2{font-size:16px;margin:0 0 10px}.label{color:var(--muted);margin-top:12px;font-size:12px}.pill{display:inline-block;padding:3px 7px;border-radius:14px;background:#eef2f8;margin:2px;max-width:100%}.gate{padding:5px 7px;border-left:3px solid #98a2b3;margin:4px 0;background:#f8fafc}.gate.READY{border-color:#12b76a}.gate.BLOCKED{border-color:#f04438}.gate.REVIEW_REQUIRED{border-color:#f79009}.empty{color:var(--muted)}
</style></head><body>
<header><h1>__TITLE__ · 需求知识图谱</h1><select id="view"><option value="hierarchy">功能层级</option><option value="er">业务对象 ER</option><option value="relations">跨功能关系</option></select><select id="module"><option value="">全部模块</option></select><input id="search" placeholder="搜索名称或 ID"><span class="stats" id="stats"></span></header><div id="notice" class="notice"></div>
<main><div id="canvas"><svg id="graph"></svg></div><aside id="detail"><h2>查看详情</h2><p class="empty">点击节点查看规则、状态、关联、评审门禁和原文证据。</p></aside></main>
<script>
const DATA=__DATA__,F=DATA.functions||[],A=DATA.atomic_functions||[],B=DATA.business_fields||[],L=DATA.field_bindings||[],O=DATA.business_objects||[],S=DATA.states||[],R=DATA.relations||[],BR=DATA.business_rules||[],FU=DATA.field_usages||[];
const byId=Object.fromEntries([...F,...A,...B,...O,...S,...BR,...FU].map(x=>[x.function_id||x.atomic_id||x.field_id||x.object_id||x.state_id||x.rule_id||x.field_usage_id,x]));
const verdict=String(DATA.audit?.verdict||'UNKNOWN').toUpperCase(),notice=document.getElementById('notice');notice.className=`notice ${verdict==='PASS'?'pass':verdict.includes('PARTIAL')?'partial':'fail'}`;notice.textContent=verdict==='PASS'?`验收状态：PASS · 图谱快照 ${DATA.meta?.graph_snapshot_id||'未编号'}`:`非最终结果 · ${verdict} · 结构通过不代表语义验收 · 不得作为下游测试用例生成的正式输入 · 图谱快照 ${DATA.meta?.graph_snapshot_id||'未编号'}`;
const moduleSelect=document.getElementById('module'),viewSelect=document.getElementById('view'),searchInput=document.getElementById('search');moduleSelect.innerHTML+=[...new Set(F.map(x=>x.module).filter(Boolean))].map(x=>`<option>${esc(x)}</option>`).join('');
stats.textContent=`${F.length} 功能 · ${A.length} 最小功能 · ${O.length} 对象 · ${B.length} 字段 · ${BR.length} 规则 · ${R.length} 关系`;
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function idOf(x){return x.function_id||x.atomic_id||x.field_id||x.object_id||x.state_id||x.rule_id||x.field_usage_id}
function nameOf(x){return x.name||x.business_name||x.value||x.statement||idOf(x)}
function line(from,to,cls=''){const p=positions[from],t=positions[to];return p&&t?`<path class="edge ${cls}" d="M${p[0]+220},${p[1]+23} C${(p[0]+t[0]+220)/2},${p[1]+23} ${(p[0]+t[0])/2},${t[1]+23} ${t[0]},${t[1]+23}"/>`:''}
let positions={};
function column(items,x,cls){return items.map((item,i)=>{const id=idOf(item),y=45+i*66;positions[id]=[x,y];return `<g class="node ${cls}" data-id="${esc(id)}" data-text="${esc((id+' '+nameOf(item)).toLowerCase())}"><rect x="${x}" y="${y}" width="220" height="44"/><text x="${x+10}" y="${y+18}">${esc(id)}</text><text x="${x+10}" y="${y+35}">${esc(nameOf(item).slice(0,24))}</text></g>`}).join('')}
function finish(nodes,edges,rows){graph.setAttribute('height',90+Math.max(rows,1)*66);graph.setAttribute('viewBox',`0 0 1180 ${90+Math.max(rows,1)*66}`);graph.innerHTML=edges+nodes;const q=searchInput.value.trim().toLowerCase();graph.querySelectorAll('.node').forEach(n=>{if(q&&!n.dataset.text.includes(q))n.classList.add('dim');n.onclick=()=>show(n.dataset.id)})}
function hierarchy(){const fs=F.filter(x=>!moduleSelect.value||x.module===moduleSelect.value),fids=new Set(fs.map(x=>x.function_id)),as=A.filter(x=>fids.has(x.function_id)),aids=new Set(as.map(x=>x.atomic_id)),links=L.filter(x=>aids.has(x.atomic_id)),bs=[...new Set(links.map(x=>x.field_id))].map(id=>byId[id]).filter(Boolean);positions={};const nodes=column(fs,35,'fun')+column(as,420,'atomic')+column(bs,825,'field');let edges='';as.forEach(x=>edges+=line(x.function_id,x.atomic_id));links.forEach(x=>edges+=line(x.atomic_id,x.field_id));finish(nodes,edges,Math.max(fs.length,as.length,bs.length))}
function er(){const objectIds=new Set(B.map(x=>x.object_id).filter(Boolean)),objects=O.filter(x=>objectIds.has(x.object_id)),fields=B,states=S;positions={};const nodes=column(objects,35,'object')+column(fields,420,'field')+column(states,825,'state');let edges='';fields.forEach(x=>edges+=line(x.object_id,x.field_id));states.forEach(x=>edges+=line(x.field_id,x.state_id));finish(nodes,edges,Math.max(objects.length,fields.length,states.length))}
function relations(){const business=R.filter(x=>['references','depends_on','state_flow','data_flow','conflict'].includes(x.type)),ids=[...new Set(business.flatMap(x=>[x.source_id,x.target_id]))],left=ids.filter((_,i)=>i%2===0).map(id=>byId[id]).filter(Boolean),right=ids.filter((_,i)=>i%2).map(id=>byId[id]).filter(Boolean);positions={};const cls=x=>x.function_id?'fun':x.atomic_id?'atomic':x.field_id?'field':'object',nodes=left.map((x,i)=>column([x],35,cls(x)).replace('y="45"',`y="${45+i*66}"`).replace(/y="63"/,`y="${63+i*66}"`).replace(/y="80"/,`y="${80+i*66}"`)).join('')+right.map((x,i)=>column([x],825,cls(x)).replace('y="45"',`y="${45+i*66}"`).replace(/y="63"/,`y="${63+i*66}"`).replace(/y="80"/,`y="${80+i*66}"`)).join('');positions={};left.forEach((x,i)=>positions[idOf(x)]=[35,45+i*66]);right.forEach((x,i)=>positions[idOf(x)]=[825,45+i*66]);let edges='';business.forEach(x=>edges+=line(x.source_id,x.target_id,x.type==='conflict'?'conflict':'cross'));finish(nodes,edges,Math.max(left.length,right.length))}
function evidence(x){return (x.evidence||[]).map(e=>`<div class="pill">${esc(e.locator)}：${esc(e.quote)}</div>`).join('')||'<span class="empty">无</span>'}
function show(id){const x=byId[id];if(!x)return;let extra='';if(x.atomic_id){const usages=FU.filter(v=>v.atomic_id===id),rules=BR.filter(v=>(v.applies_to_ids||[]).includes(id)),relations=R.filter(v=>v.source_id===id||v.target_id===id),gates=x.quality_review?.dimension_eligibility||{};extra=`<div class="label">触发与动作</div><div>${esc(x.trigger)} → ${esc(x.action)}</div><div class="label">字段使用</div>${usages.map(v=>`<div class="pill">${esc(byId[v.field_id]?.business_name||v.field_id)} · ${esc((v.usages||[]).join('/'))}</div>`).join('')||'<span class="empty">无</span>'}<div class="label">业务规则</div>${rules.map(v=>`<div class="pill">${esc(v.category)} · ${esc(v.statement)}</div>`).join('')||'<span class="empty">无</span>'}<div class="label">测试维度门禁</div>${Object.entries(gates).map(([k,v])=>`<div class="gate ${esc(v.status)}">${esc(k)} · ${esc(v.status)} ${esc((v.reasons||[]).join('；'))}</div>`).join('')||'<span class="empty">尚未投影评审</span>'}<div class="label">跨功能关系</div>${relations.filter(v=>!['contains','uses_field','constrained_by'].includes(v.type)).map(v=>`<div class="pill">${esc(v.type)} · ${esc(v.source_id)} → ${esc(v.target_id)}</div>`).join('')||'<span class="empty">无</span>'}`}
if(x.field_id){const usages=FU.filter(v=>v.field_id===id),rules=BR.filter(v=>(v.applies_to_ids||[]).includes(id)),states=S.filter(v=>v.field_id===id);extra=`<div class="label">业务对象</div><div>${esc(x.business_object)}</div><div class="label">内在规则</div>${rules.map(v=>`<div class="pill">${esc(v.category)} · ${esc(v.statement)}</div>`).join('')||'<span class="empty">无</span>'}<div class="label">使用位置</div>${usages.map(v=>`<div class="pill">${esc(byId[v.atomic_id]?.name||v.atomic_id)} · ${esc((v.usages||[]).join('/'))}</div>`).join('')}<div class="label">状态枚举</div>${states.map(v=>`<span class="pill">${esc(v.value)}</span>`).join('')||'<span class="empty">无</span>'}`}
if(x.object_id){extra=`<div class="label">字段</div>${B.filter(v=>v.object_id===id).map(v=>`<div class="pill">${esc(v.business_name)} · ${esc(v.field_id)}</div>`).join('')}`}
if(x.state_id){extra=`<div class="label">所属字段</div><div>${esc(byId[x.field_id]?.business_name||x.field_id)}</div>`}
detail.innerHTML=`<h2>${esc(nameOf(x))}</h2><div>${esc(id)}</div>${extra}<div class="label">原文证据</div>${evidence(x)}`}
function render(){({hierarchy,er,relations}[viewSelect.value]||hierarchy)()}viewSelect.onchange=render;moduleSelect.onchange=render;searchInput.oninput=render;render();
</script></body></html>'''


if __name__ == "__main__":
    raise SystemExit(main())
