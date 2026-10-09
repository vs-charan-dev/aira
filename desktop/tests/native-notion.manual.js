// Explicit integration diagnostic; creates one fixed private synthetic note.
// Not included by the *.cjs test glob. Never run as part of automated tests.
const { DesktopActions } = require('../actions.cjs');
const path = require('node:path');
const controller = new DesktopActions({root:path.resolve(__dirname,'../..'),onState:state=>console.log(JSON.stringify(state))});
controller.run({kind:'create_notion_note',title:'AIRA end-to-end demo 2026-10-08',content:'Prepare the Memory Palace demo.\nCheck desktop voice controls.'},'native-notion-check').then(result=>{
  console.log(JSON.stringify(result));
  if(result.status!=='succeeded') process.exitCode=1;
});
