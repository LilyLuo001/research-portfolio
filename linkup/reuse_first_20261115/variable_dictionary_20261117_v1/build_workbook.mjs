import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

// Metadata only. Authoring dependencies are the configured workspace runtime.
const [inputDir, outputDir] = process.argv.slice(2);
if (!inputDir || !outputDir) throw new Error('Expected metadata input and output directories');
await fs.mkdir(outputDir,{recursive:true});
const read = async n => JSON.parse(await fs.readFile(path.join(inputDir,n),'utf8'));
const d=await read('VARIABLE_DICTIONARY_PUBLIC.json');
const m=await read('REUSE_MAPPING_PUBLIC.json');
const g=await read('FIELD_GAPS_PUBLIC.json');
const c=await read('LEGACY_FIELD_COVERAGE_PUBLIC.json');
const s=await read('SOURCES_AND_SCOPE_PUBLIC.json');
const a=await read('ASSET_INVENTORY_PUBLIC.json');
const wb=Workbook.create();
const vars=new Map(d.variables.map(v=>[v.variable_key,v]));
const clean=x => x==null ? '未核清' : typeof x==='object' ? JSON.stringify(x) : x;
const shortStatus={structural_reuse:'已有结构数据',partial_semantic_reuse:'部分原语义可复用',derive_pending:'待派生/拼接',new_definition:'需新增结构/分类',external_pending:'待外部数据'};
const tableInfo=[];
function table(name,title,note,headers,rows,widths,height=70){
  const sh=wb.worksheets.add(name);sh.showGridLines=false;
  const end=String.fromCharCode(64+headers.length), last=rows.length+5;
  sh.getRange(`A2:${end}${last}`).format.font={name:'Arial',size:11,color:'#1E293B'};
  sh.getRange('A2').values=[[title]];sh.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:'#17365D'};
  sh.getRange('A3').values=[[note]];sh.getRange('A3').format.font={name:'Arial',size:10,color:'#475569'};
  sh.getRange(`A5:${end}${last}`).values=[headers,...rows.map(r=>r.map(clean))];
  sh.getRange(`A5:${end}5`).format={fill:'#243E60',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,verticalAlignment:'center',horizontalAlignment:'center',rowHeight:32};
  sh.getRange(`A6:${end}${last}`).format.wrapText=true;
  sh.getRange(`A6:${end}${last}`).format.verticalAlignment='top';
  sh.getRange(`A6:${end}${last}`).format.rowHeight=height;
  widths.forEach((w,i)=>sh.getRangeByIndexes(0,i,last,1).format.columnWidth=w);
  for(let r=6;r<=last;r++) if(r%2===0)sh.getRange(`A${r}:${end}${r}`).format.fill='#F1F5F9';
  sh.tables.add(`A5:${end}${last}`,true,`Table${tableInfo.length+1}`);
  // Fit prose rows individually; do not force sparse rows into large blank bands.
  const weighted=s=>[...String(s)].reduce((n,ch)=>n+(ch.charCodeAt(0)>255?2:1),0);
  rows.forEach((row,i)=>{
    const lines=Math.max(...row.map((v,j)=>String(clean(v)).split('\n').reduce((n,line)=>n+Math.max(1,Math.ceil(weighted(line)/Math.max(12,widths[j]*0.9))),0)));
    sh.getRange(`A${i+6}:${end}${i+6}`).format.rowHeight=Math.max(34,lines*16+10);
  });
  sh.freezePanes.freezeRows(5);sh.freezePanes.freezeColumns(2);
  sh.tabColor=tableInfo.length===0?'#243E60':'#8CA3BC';
  tableInfo.push({name,rows:rows.length,columns:headers.length,last,end});
  return sh;
}
table('缺口总览','LinkUp 变量与旧成果复用 v1.0.0','89个定义 / 139条映射 / 15类旧资产。不是新增广告数；完整交付净缺口仍未核清。',
 ['字段组','已有与可复用','真正缺什么','下一步','当前层级'],
 g.rows.map(r=>[r.field_group,r.verified_existing,r.actual_gap,r.next_action,r.reuse_status]),[22,58,58,54,30],90);
table('变量字典','版本化变量字典','每个变量有稳定ID；五模块均保留。版本化定义不等于原生产schema已被替换。',
 ['变量名称','稳定变量ID','模块','已有状态','定义','剩余工作','单位与类型','取值或单位','依赖与伴随绑定','来源引用'],
 d.variables.map(v=>[v.label_zh,v.variable_key,v.modules.map(x=>d.modules[x]).join('、'),shortStatus[v.availability_code]||v.availability_zh,v.definition_zh,v.remaining_work_zh,v.unit+' / '+v.type,v.allowed_values_or_units,[...v.dependencies,...(v.required_companion_bindings||[]),...Object.values(v.conditional_dependencies||{}).flat(),...(v.external_dependencies||[])].join('；'),v.source_refs.join(', ')]),
 [25,35,22,25,66,60,30,52,60,35],105);
table('旧成果映射','旧成果复用映射','同广告不等于同正文；原mask/版本/条款锚点共同保留。候选结果不自动升级为新语义真值。',
 ['变量名称','稳定变量ID','旧资产','原字段或选择器','复用方式','覆盖口径','仍缺什么','转换要求','来源引用'],
 m.rows.map(r=>[vars.get(r.variable_key).label_zh,r.variable_key,r.asset_key,r.source_selector,r.reuse_mode,r.coverage_basis_zh,r.remaining_or_blocking_zh,r.transform_zh,r.source_refs.join(', ')]),
 [25,35,37,68,42,66,64,55,35],110);
const coverage=[];
for(const asset of ['Pro','fixed10k']) for(const [field,states] of Object.entries(c.field_status_counts[asset]))for(const [st,n] of Object.entries(states))coverage.push([asset,field,st,n,asset==='Pro'?'上下文×原维度':'广告×原字段族',asset==='Pro'?'历史投影31,690上下文；非完整新字典覆盖':'原10,000广告；每族分母独立；不与Pro相加']);
const cov=table('历史字段覆盖','旧字段状态投影','保留历史分母。unknown不是未处理；不同字段、资产和样本单位不能相加估算全量缺口。',
 ['资产','原字段或字段族','原状态','数量','单位','范围说明'],coverage,[18,60,34,16,28,65],48);
cov.getRange(`D6:D${coverage.length+5}`).setNumberFormat('#,##0');
table('资产与来源','已核旧资产与来源','15类资产；完整物理字段和SHA见配套JSON。这里只列已有证据，不宣称逐行数据本轮全部重验。',
 ['资产','已有范围','可用性','原验收层','新语义资格','注意事项','证据来源'],
 a.assets.map(v=>[v.asset_id,v.scope,v.availability,v.original_acceptance,v.new_semantic_qualification,v.cautions.join('；'),v.evidence.map(e=>a.source_manifest[e.source]?.repository_path||e.source).join('\n')]),
 [40,62,55,60,46,85,85],170);
wb.recalculate();
const inspections=[];
for(const t of tableInfo){
  inspections.push((await wb.inspect({kind:'table',range:`'${t.name}'!A5:F7`,include:'values,formulas',tableMaxRows:3,tableMaxCols:6,maxChars:1400})).ndjson);
  const last=await wb.inspect({kind:'table',range:`'${t.name}'!A${t.last}:D${t.last}`,include:'values',tableMaxRows:1,maxChars:800});inspections.push(last.ndjson);
  const blob=await wb.render({sheetName:t.name,range:`A1:${t.name==='缺口总览'?'E':'F'}${t.name==='资产与来源'?7:9}`,scale:1,format:'png'});
  await fs.writeFile(path.join(outputDir,`preview_${t.name}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30},maxChars:2000});
await fs.writeFile(path.join(outputDir,'inspection_PRIVATE.txt'),inspections.join('\n')+'\n'+errors.ndjson);
const file=await SpreadsheetFile.exportXlsx(wb);const dest=path.join(outputDir,'LinkUp_变量字典与复用映射_v1.0.0.xlsx');await file.save(dest);
const bytes=await fs.readFile(dest);
await fs.writeFile(path.join(inputDir,'WORKBOOK_RECEIPT_PUBLIC.json'),JSON.stringify({version:d.dictionary_version,status:'exported_pending_visual_review',sheets:tableInfo.map(t=>({sheet:t.name,rows:t.rows,columns:t.columns})),sha256:crypto.createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,formulas_used:false,metadata_only:true,source_dictionary_sha256:crypto.createHash('sha256').update(await fs.readFile(path.join(inputDir,'VARIABLE_DICTIONARY_PUBLIC.json'))).digest('hex')},null,2)+'\n');
console.log(JSON.stringify({status:'exported',bytes:bytes.length,sheets:tableInfo.length,variables:d.variables.length,mappings:m.rows.length}));
