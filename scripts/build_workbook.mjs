import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const D=JSON.parse(await fs.readFile(path.join(root,'outputs/analysis.json'),'utf8'));
const out=path.join(root,'outputs/audi-2314893');
const qa=path.join(root,'tmp/workbook');
await fs.mkdir(out,{recursive:true});await fs.mkdir(qa,{recursive:true});
const wb=Workbook.create(),names=['Review','Controls','Plan','Costs','Evidence','Actions','Risks'];
const sheets=Object.fromEntries(names.map(n=>[n,wb.worksheets.add(n)]));
const color={ink:'#18232B',grey:'#65706D',line:'#D4DCD5',red:'#A82D39',input:'#FFF1CB',green:'#24704B'};
function write(s,cell,values){s.getRange(cell).write(values)}
function value(s,cell,v){s.getRange(cell).values=[[v]]}
function formula(s,cell,f){s.getRange(cell).formulas=[[f]]}
function heading(s,title,end='L'){value(s,'A2',title);s.getRange(`A2:${end}2`).format.font={name:'Arial',size:16,bold:true,color:color.ink};s.getRange(`A3:${end}3`).format.borders={bottom:{style:'thin',color:color.line}}}
function header(s,range){s.getRange(range).format={fill:color.ink,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:32,verticalAlignment:'center',horizontalAlignment:'center',wrapText:true};s.getRange(range).format.borders={insideVertical:{style:'thin',color:'#FFFFFF'}}}
function input(s,range){s.getRange(range).format.fill=color.input;s.getRange(range).format.font.color='#174E88'}
function num(s,range,fmt='#,##0'){s.getRange(range).setNumberFormat(fmt);s.getRange(range).format.horizontalAlignment='right'}
function notes(s,row,text){value(s,`A${row}`,text);s.getRange(`A${row}:N${row}`).format.font={name:'Arial',size:10,color:color.grey};s.getRange(`A${row}:N${row}`).format.rowHeight=22}
for(const [n,s] of Object.entries(sheets)){s.showGridLines=false;s.getRange('A1:Z55').format.font={name:'Arial',size:10,color:color.ink};s.getRange('A1:Z55').format.rowHeight=23;s.getRange('A1:Z55').format.columnWidth=14;s.getRange('A1:Z55').format.verticalAlignment='center';heading(s,n==='Review'?'Power unit programme review':n==='Plan'?'Activity plan and resource sequence':n==='Costs'?'Cost control':n==='Evidence'?'Release acceptance records':n==='Risks'?'Risk register':n==='Actions'?'Programme actions':'Forecast controls');}
sheets.Review.tabColor=color.ink;sheets.Controls.tabColor='#60727A';
const control=sheets.Controls;
write(control,'A4',[['Case Selected:',1,null,null],['Case key','1 Current; 2 Expedite; 3 Recovery',null,null]]);
formula(control,'D4','=CHOOSE(B4,"Current forecast","Expedite supply","Coordinated recovery")');
input(control,'B4');control.getRange('B4').dataValidation={rule:{type:'list',values:['1','2','3']}};
control.getRange('A4:A12').format.columnWidth=31;control.getRange('B4:B12').format.columnWidth=26;control.getRange('D4:G4').format.columnWidth=20;
const excelStart=(Date.parse(D.config.start_date+'T00:00:00Z')-Date.UTC(1899,11,30))/86400000;
write(control,'A7',[['Programme start',excelStart],['Status day',D.config.status_day],['Committed finish day',D.config.target_day],['Late support EUR per workday',D.config.delay_cost_per_day]]);
control.getRange('B7').setNumberFormat('dd-mmm-yyyy');
notes(control,12,'Amber cells are editable. Day zero is the programme start. Five-day week; no holiday exclusions.');
const drivers=['ERS03','ERS04','INT03','INT08','PM04'];
const activeRows={};let cr=15;
for(const id of drivers){activeRows[id]=cr;const task=D.tasks.find(t=>t.id===id);write(control,`A${cr}`,[['Active remaining days '+id,null],['Current forecast',task.remaining_days],['Expedite supply',D.config.cases[1].task_changes[id]?.remaining_days??task.remaining_days],['Coordinated recovery',D.config.cases[2].task_changes[id]?.remaining_days??task.remaining_days]]);formula(control,`B${cr}`,`=IF(CHOOSE($B$4,ISNUMBER(B${cr+1}),ISNUMBER(B${cr+2}),ISNUMBER(B${cr+3})),INDEX(B${cr+1}:B${cr+3},$B$4),NA())`);control.getRange(`A${cr}:B${cr}`).format.font.bold=true;input(control,`B${cr+1}:B${cr+3}`);control.dataValidations.add({range:`B${cr+1}:B${cr+3}`,rule:{type:'whole',operator:'between',formula1:1,formula2:1000}});cr+=5;}
const feeRow=cr;write(control,`A${cr}`,[['Active recovery cost EUR',null],['Current forecast',0],['Expedite supply',18000],['Coordinated recovery',31000]]);formula(control,`B${cr}`,`=IF(CHOOSE($B$4,ISNUMBER(B${cr+1}),ISNUMBER(B${cr+2}),ISNUMBER(B${cr+3})),INDEX(B${cr+1}:B${cr+3},$B$4),NA())`);input(control,`B${cr+1}:B${cr+3}`);num(control,`B${cr}:B${cr+3}`,'"€"#,##0;("€"#,##0);"€"0');
notes(control,46,'Recovery changes remaining estimates only. Actuals and acceptance records do not change with the selector.');
notes(control,48,'Scenario inputs are fictional assumptions. Source: data/config.json and data/tasks.csv in this project.');
const plan=sheets.Plan,start=7,last=start+D.tasks.length-1;
const rowOf=Object.fromEntries(D.tasks.map((t,i)=>[t.id,start+i]));
const current=D.cases[0].forecast.tasks;
const headers=['ID','Activity','Workstream','Resource','Physical progress','Baseline finish day','Source remaining days','Active remaining days','Actual start day','Actual finish day','Forecast start day','Forecast finish day','Finish variance days','Forecast finish date','Latest finish day','Latest start day','Total float days','Critical remaining','Owner','Budget EUR','Actual EUR','Remaining cost EUR','Predecessors incl. resource','Input status'];
write(plan,'A6',[headers]);header(plan,'A6:X6');
value(plan,'A4','Case Selected:');formula(plan,'C4',"='Controls'!D4");
plan.getRange('B1:B55').format.columnWidth=45;plan.getRange('C1:D55').format.columnWidth=15;plan.getRange('S1:S55').format.columnWidth=23;plan.getRange('W1:W55').format.columnWidth=29;plan.getRange('X1:X55').format.columnWidth=31;
plan.freezePanes.freezeRows(6);plan.freezePanes.freezeColumns(2);
const successors=Object.fromEntries(D.tasks.map(t=>[t.id,[]]));
for(const t of D.tasks)for(const p of current[t.id].preds)successors[p].push(t.id);
const planRows=D.tasks.map(t=>[t.id,t.name,t.stream,t.resource,t.progress,D.baseline.tasks[t.id].finish,t.remaining_days,null,t.actual_start,t.actual_finish,null,null,null,null,null,null,null,null,t.owner,t.budget,t.actual_cost,t.etc,current[t.id].preds.join(';'),null]);
write(plan,'A7',planRows);
for(const t of D.tasks){const r=rowOf[t.id],preds=current[t.id].preds;formula(plan,`H${r}`,activeRows[t.id]?`='Controls'!B${activeRows[t.id]}`:`=IF(ISNUMBER(G${r}),G${r},NA())`);
const earliest=`MAX('Controls'!$B$8,${t.ready_day}${preds.length?','+preds.map(p=>`L${rowOf[p]}`).join(','):''})`;
formula(plan,`K${r}`,`=IF(E${r}=1,I${r},${earliest})`);
formula(plan,`L${r}`,`=IF(E${r}=1,J${r},K${r}+H${r})`);
formula(plan,`M${r}`,`=L${r}-F${r}`);formula(plan,`N${r}`,`=WORKDAY('Controls'!$B$7,L${r})`);
formula(plan,`O${r}`,successors[t.id].length?`=MIN(${successors[t.id].map(i=>`P${rowOf[i]}`).join(',')})`:`=MAX($L$${start}:$L$${last})`);
formula(plan,`P${r}`,`=O${r}-(L${r}-K${r})`);formula(plan,`Q${r}`,`=P${r}-K${r}`);formula(plan,`R${r}`,`=IF(AND(E${r}<1,Q${r}=0),"Yes","No")`);
formula(plan,`X${r}`,`=IF(OR(NOT(ISNUMBER(E${r})),E${r}<0,E${r}>1,NOT(ISNUMBER(H${r})),H${r}<0),"Invalid progress or duration",IF(AND(E${r}=1,OR(NOT(ISNUMBER(I${r})),NOT(ISNUMBER(J${r})),J${r}>'Controls'!$B$8,H${r}<>0,V${r}<>0)),"Completed task inconsistent",IF(AND(E${r}<1,J${r}<>""),"Unfinished task has finish","OK")))`);
}
input(plan,`G${start}:G${last}`);num(plan,`E${start}:E${last}`,'0%');num(plan,`F${start}:M${last}`);num(plan,`N${start}:N${last}`,'dd-mmm-yyyy');num(plan,`O${start}:Q${last}`);num(plan,`T${start}:V${last}`,'#,##0;(#,##0);0');
plan.dataValidations.add({range:`G${start}:G${last}`,rule:{type:'whole',operator:'between',formula1:0,formula2:1000}});
plan.getRange(`M${start}:M${last}`).conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:'#F7E5E4',font:{color:'#9E2934'}}});
plan.getRange(`R${start}:R${last}`).conditionalFormats.add('containsText',{text:'Yes',format:{fill:'#F7E5E4',font:{color:'#9E2934',bold:true}}});
plan.getRange(`X${start}:X${last}`).conditionalFormats.addCustom(`$X${start}<>"OK"`,{fill:'#F7E5E4',font:{color:'#9E2934'}});
notes(plan,47,'Resource order is fixed to the reference plan in this workbook. Python can fill newly available gaps when rebuilding.');
notes(plan,49,'After changing priorities, topology, actual status or resource capacity, rebuild from Python and review the new sequence.');
notes(plan,51,'Source: fictional data/tasks.csv. Baseline is frozen. Remaining durations are owner estimates independent of physical progress.');
const costs=sheets.Costs;value(costs,'A4','Case Selected:');formula(costs,'C4',"='Controls'!D4");costs.getRange('A1:A55').format.columnWidth=17;costs.getRange('B1:B55').format.columnWidth=22;
header(costs,'A6:H6');write(costs,'A6',[['ID','Workstream','Budget EUR','Planned value EUR','Earned value EUR','Actual EUR','ETC EUR','Bottom up EAC EUR']]);
for(const t of D.tasks){const r=rowOf[t.id],b=D.baseline.tasks[t.id];write(costs,`A${r}`,[[t.id,t.stream,null,null,null,null,null,null]]);formula(costs,`C${r}`,`='Plan'!T${r}`);formula(costs,`D${r}`,t.baseline_days?`=C${r}*MIN(1,MAX(0,('Controls'!$B$8-${b.start})/${t.baseline_days}))`:`=IF('Controls'!$B$8>=${b.finish},C${r},0)`);formula(costs,`E${r}`,`=C${r}*'Plan'!E${r}`);formula(costs,`F${r}`,`='Plan'!U${r}`);formula(costs,`G${r}`,`='Plan'!V${r}`);formula(costs,`H${r}`,`=F${r}+G${r}`);}
for(const c of ['C','D','E','F','G','H'])formula(costs,`${c}46`,`=SUM(${c}7:${c}${last})`);
num(costs,`C7:H46`,'#,##0;(#,##0);0');costs.getRange('A46:H46').format.font.bold=true;costs.freezePanes.freezeRows(6);notes(costs,49,'Linear baseline phasing defines planned value. Earned value = budget × physical progress. No average of task-level ratios.');notes(costs,51,'Programme recovery and late support are separate in Review. Source: fictional task-level budgets, actuals and owner ETC.');
const evidence=sheets.Evidence;value(evidence,'A4','Case Selected:');formula(evidence,'C4',"='Controls'!D4");write(evidence,'A6',[['ID','Mandatory','Linked task','Record state','Evidence reference','Approver','Acceptance day','Task complete','Acceptance result','Owner']]);header(evidence,'A6:J6');
evidence.getRange('E1:F30').format.columnWidth=26;evidence.getRange('I1:J30').format.columnWidth=25;
for(let n=0;n<D.cases[0].readiness.rows.length;n++){const e=D.cases[0].readiness.rows[n],r=7+n,tr=rowOf[e.task_id];write(evidence,`A${r}`,[[e.id,e.mandatory?'Yes':'No',e.task_id,e.state,e.reference,e.approver,e.accepted_day,null,null,e.owner]]);formula(evidence,`H${r}`,`=IF('Plan'!E${tr}=1,"Yes","No")`);formula(evidence,`I${r}`,`=IF(AND(D${r}="Accepted",LEN(TRIM(E${r}))>0,LEN(TRIM(F${r}))>0,ISNUMBER(G${r}),G${r}>=0,G${r}<='Controls'!$B$8,H${r}="Yes"),"Accepted","Not accepted")`);}
input(evidence,'D7:G18');evidence.getRange('D7:D18').dataValidation={rule:{type:'list',values:['Missing','In review','Accepted','Rejected']}};
evidence.getRange('I7:I18').conditionalFormats.add('containsText',{text:'Not accepted',format:{fill:'#FFF0DB',font:{color:'#885614'}}});
evidence.freezePanes.freezeRows(6);notes(evidence,21,'Synthetic acceptance rule: completed work + Accepted state + reference + approver + a valid date.');notes(evidence,23,'An earlier forecast date never accepts evidence. DEMO references are fictional, not actual technical records.');
const actions=sheets.Actions;write(actions,'A6',[['ID','Owner','Due day','Due date','State','Linked risk or decision','Action','Overdue']]);header(actions,'A6:H6');actions.getRange('B1:B30').format.columnWidth=25;actions.getRange('G1:G30').format.columnWidth=82;
for(let n=0;n<D.actions.length;n++){const a=D.actions[n],r=7+n;write(actions,`A${r}`,[[a.id,a.owner,a.due_day,null,a.state,a.linked,a.action,null]]);formula(actions,`D${r}`,`=WORKDAY('Controls'!$B$7,C${r})`);formula(actions,`H${r}`,`=IF(AND(E${r}<>"Closed",C${r}<'Controls'!$B$8),"Yes","No")`);}
input(actions,'C7:C11');input(actions,'E7:E11');actions.getRange('E7:E11').dataValidation={rule:{type:'list',values:['Open','In progress','Closed']}};num(actions,'D7:D11','dd-mmm-yyyy');actions.getRange('G7:G11').format.wrapText=true;actions.getRange('A7:H11').format.rowHeight=45;notes(actions,15,'Due dates and state support a weekly review. All roles and actions in this demonstrator are fictional.');
const risks=sheets.Risks;write(risks,'A6',[['ID','Risk','Owner','Reference probability','Affected activities','Trigger','Mitigation']]);header(risks,'A6:G6');risks.getRange('B1:B20').format.columnWidth=35;risks.getRange('C1:C20').format.columnWidth=23;risks.getRange('F1:G20').format.columnWidth=65;
for(let n=0;n<D.risks.length;n++){const r=D.risks[n];write(risks,`A${n+7}`,[[r.id,r.name,r.owner,r.probability??'n.a.',r.affected_tasks.join('\n'),r.trigger,r.mitigation]]);}
risks.getRange('B7:G10').format.wrapText=true;risks.getRange('A7:G10').format.rowHeight=73;num(risks,'D7:D10','0%');notes(risks,14,'Reference probabilities are illustrative. The Python simulation uses scenario-specific assumptions from config.json.');notes(risks,16,'Monte Carlo is not recalculated in Excel. Regenerate the report after edits; saved simulation outputs are in analysis.json.');notes(risks,18,'Public method reference: https://www.gao.gov/products/gao-16-89g');
const review=sheets.Review;review.getRange('A1:A55').format.columnWidth=32;review.getRange('B1:B55').format.columnWidth=23;review.getRange('C1:C55').format.columnWidth=4;review.getRange('D1:D55').format.columnWidth=25;review.getRange('E1:E55').format.columnWidth=21;
value(review,'A4','Case Selected:');formula(review,'B4',"='Controls'!D4");review.getRange('B4').format.font.color=color.green;value(review,'D4','Fictional independent case study');
write(review,'A6',[['Delivery',null,null,'Cost forecast EUR',null]]);header(review,'A6:B6');header(review,'D6:E6');
write(review,'A7',[['Forecast finish day'],['Committed finish day'],['Forecast finish boundary'],['Baseline finish day'],['Days beyond commitment'],['Release acceptance'],['Accepted mandatory records'],['Total mandatory records'],['Plan input status']]);
formula(review,'B7',`=MAX('Plan'!L7:L${last})`);formula(review,'B8',"='Controls'!B9");formula(review,'B9',"=WORKDAY('Controls'!B7,B7)");formula(review,'B10',`=${D.baseline.finish}`);formula(review,'B11','=MAX(0,B7-B8)');formula(review,'B13',"=COUNTIFS('Evidence'!B7:B18,\"Yes\",'Evidence'!I7:I18,\"Accepted\")");formula(review,'B14',"=COUNTIF('Evidence'!B7:B18,\"Yes\")");formula(review,'B12','=IF(AND(B14>0,B13=B14),"Ready for decision","Blocked by evidence")');formula(review,'B15',`=IF(COUNTIF('Plan'!X7:X${last},"<>OK")=0,"Inputs consistent","Review Plan input errors")`);num(review,'B9','dd-mmm-yyyy');
write(review,'D7',[['Baseline budget'],['Actual cost'],['Owner ETC'],['Recovery spending'],['Late support'],['Forecast cost at completion'],['Forecast over baseline'],['Schedule performance index'],['Cost performance index']]);
formula(review,'E7',"='Costs'!C46");formula(review,'E8',"='Costs'!F46");formula(review,'E9',"='Costs'!G46");formula(review,'E10',`='Controls'!B${feeRow}`);formula(review,'E11',"=B11*'Controls'!B10");formula(review,'E12','=SUM(E8:E11)');formula(review,'E13','=E12-E7');formula(review,'E14',"=IF('Costs'!D46=0,\"n.a.\",'Costs'!E46/'Costs'!D46)");formula(review,'E15',"=IF('Costs'!F46=0,\"n.a.\",'Costs'!E46/'Costs'!F46)");num(review,'E7:E13','"€"#,##0;("€"#,##0);"€"0');num(review,'E14:E15','0.000');review.getRange('D12:E12').format.font.bold=true;
review.getRange('B11').conditionalFormats.add('cellIs',{operator:'greaterThan',formula:0,format:{fill:'#F7E5E4',font:{color:'#9E2934'}}});review.getRange('B12').conditionalFormats.add('containsText',{text:'Blocked',format:{fill:'#FFF0DB',font:{color:'#885614'}}});
write(review,'A19',[['Next programme decisions'],['D01 Confirm the supplier dispatch commitment and recovery quote.'],['D02 Protect the test-resource sequence and retain validation scope.'],['D03 Accept release evidence separately from the schedule forecast.']]);
review.getRange('A19:E19').format.font.bold=true;
write(review,'A25',[['Workstream','Budget EUR',null,'Actual plus ETC EUR']]);header(review,'A25:B25');header(review,'D25:D25');
const streams=[...new Set(D.tasks.map(t=>t.stream))];for(let n=0;n<streams.length;n++){const r=26+n;value(review,`A${r}`,streams[n]);formula(review,`B${r}`,`=SUMIF('Costs'!B7:B${last},A${r},'Costs'!C7:C${last})`);formula(review,`D${r}`,`=SUMIF('Costs'!B7:B${last},A${r},'Costs'!H7:H${last})`);}
num(review,'B26:B30','"€"#,##0');num(review,'D26:D30','"€"#,##0');
const chart=review.charts.add('bar',[review.getRange('A25:A30'),review.getRange('B25:B30'),review.getRange('D25:D30')]);chart.title='Workstream budget and remaining forecast';chart.titleTextStyle.fontSize=12;chart.titleTextStyle.typeface='Arial';chart.setPosition('G6','O22');chart.xAxis={axisType:'textAxis',textStyle:{typeface:'Arial',fontSize:10}};chart.yAxis={numberFormatCode:'"€"0,"k"',numberFormatSourceLinked:false,textStyle:{typeface:'Arial',fontSize:10}};chart.legend={position:'bottom',textStyle:{typeface:'Arial',fontSize:10}};chart.series.items[0].fill='#C6CDCA';chart.series.items[1].fill='#354B60';
notes(review,33,'Change the case selector and amber assumptions in Controls. Plan and cost results recalculate.');notes(review,35,'Workbook uses a fixed resource order. Rebuild in Python if the order, dependencies or source status changes.');notes(review,37,'The offline report contains the stochastic analysis. Monte Carlo results do not recalculate in this workbook.');notes(review,39,'Fictional demonstrator work package. EUR figures are not Audi data or a full F1 programme budget.');
// Verify all three cases against the independent Python engine using this fixed sequence.
const checks=[];
for(let i=0;i<3;i++){value(control,'B4',i+1);wb.recalculate();const finish=review.getRange('B7').values[0][0],eac=review.getRange('E12').values[0][0];const expected=D.cases[i];if(finish!==expected.forecast.finish||Math.abs(eac-expected.eac)>.01)throw new Error('Workbook/Python mismatch '+expected.id+': '+JSON.stringify({finish,eac,expected:expected.forecast.finish,cost:expected.eac}));checks.push({case:expected.id,finish,eac});}
// A later-period input change must propagate through the same build.
value(control,'B4',3);const before=review.getRange('B7').values[0][0];const lateRow=activeRows.PM04;const old=control.getRange(`B${lateRow+3}`).values[0][0];value(control,`B${lateRow+3}`,old+2);wb.recalculate();if(review.getRange('B7').values[0][0]!==before+2)throw new Error('Later duration did not propagate');value(control,`B${lateRow+3}`,old);
// One accepted record cannot clear another record and cannot accept incomplete work.
value(sheets.Evidence,'D10','Accepted');value(sheets.Evidence,'E10','DEMO-TEMP');value(sheets.Evidence,'F10','Lead');value(sheets.Evidence,'G10',30);wb.recalculate();if(sheets.Evidence.getRange('I10').values[0][0]!=='Not accepted')throw new Error('Incomplete work accepted');
const original=D.cases[0].readiness.rows[3];write(sheets.Evidence,'D10',[[original.state,original.reference,original.approver,original.accepted_day]]);
value(control,'B4',1);wb.recalculate();
// Missing input in an unselected option must not block the valid active option.
const selectedSource=control.getRange('B16').values[0][0],unselectedSource=control.getRange('B17').values[0][0];
value(control,'B17',null);wb.recalculate();if(review.getRange('B7').values[0][0]!==96)throw new Error('Unselected missing input blocked valid case');
value(control,'B17',unselectedSource);value(control,'B16',null);wb.recalculate();if(typeof review.getRange('B7').values[0][0]==='number')throw new Error('Missing active duration produced a plausible finish');value(control,'B16',selectedSource);
value(control,`B${feeRow+1}`,null);wb.recalculate();if(typeof review.getRange('E12').values[0][0]==='number')throw new Error('Missing spending input became zero');value(control,`B${feeRow+1}`,0);wb.recalculate();if(review.getRange('E12').values[0][0]!==D.cases[0].eac)throw new Error('Valid zero spending rejected');
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},summary:'Final formula scan',maxChars:2500});
await fs.writeFile(path.join(qa,'formula_scan.ndjson'),errors.ndjson);
await fs.writeFile(path.join(qa,'checks.json'),JSON.stringify({cases:checks,later_duration_propagation:true,unfinished_evidence_blocked:true,unselected_blank_ignored:true,active_blank_exposed:true,zero_spending_preserved:true},null,2));
for(const [name,range] of [['Review','A1:O40'],['Controls','A1:F46'],['Plan','A1:H16'],['Plan-detail','H1:R16'],['Costs','A1:H16'],['Evidence','A1:J20'],['Actions','A1:H13'],['Risks','A1:G12']]){const img=await wb.render({sheetName:name.startsWith('Plan-')?'Plan':name,range,scale:1.5,format:'png'});await fs.writeFile(path.join(qa,name+'.png'),new Uint8Array(await img.arrayBuffer()));}
const blob=await SpreadsheetFile.exportXlsx(wb);await blob.save(path.join(out,'Power_Unit_Programme_Control.xlsx'));
console.log(JSON.stringify({output:path.join(out,'Power_Unit_Programme_Control.xlsx'),checks,formulaScan:errors.ndjson},null,2));
