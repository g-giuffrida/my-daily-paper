const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');
const script = readFileSync(join(__dirname,'../components/storage/index.html'),'utf8').split('<script>')[1].split('</script>')[0];

function browser(saved, failRead=false, failWrite=false) {
  const messages=[];
  let callback, stored=saved;
  const parent={postMessage:m=>messages.push(m)};
  const ctx={parent, window:{addEventListener:(_,fn)=>callback=fn}, localStorage:{getItem:()=>{if(failRead)throw Error('disabled');return stored},setItem:(_,v)=>{if(failWrite)throw Error('quota');stored=v}}};
  vm.runInNewContext(script,ctx);
  return {messages, render:args=>callback({source:parent,data:{type:'streamlit:render',args}}),read:()=>JSON.parse(stored || '{}')};
}

test('restore once, save changes, survive a fresh browser session',()=>{
  const original={version:2,settings:{name:'My paper'},history:[]};
  const b=browser(JSON.stringify(original));
  b.render({profile:null});
  assert.equal(b.messages.find(m=>m.type==='streamlit:setComponentValue').value.profile.settings.name,'My paper');
  const updated={...original,settings:{name:'A new name'}};
  b.render({profile:updated});
  assert.deepEqual(b.read(),updated);
  assert.equal(b.messages.filter(m=>m.type==='streamlit:setComponentValue').length,1);
  const restart=browser(JSON.stringify(b.read()));restart.render({profile:null});
  assert.equal(restart.messages.find(m=>m.type==='streamlit:setComponentValue').value.profile.settings.name,'A new name');
});
test('profiles remain isolated between browser storage contexts',()=>{
  const a=browser(),b=browser();
  a.render({profile:{settings:{name:'A'}}});b.render({profile:{settings:{name:'B'}}});
  assert.equal(a.read().settings.name,'A');assert.equal(b.read().settings.name,'B');
});
test('disabled or corrupt storage warns without hanging hydration',()=>{
  for(const b of [browser('bad json'),browser(null,true)]){
    b.render({profile:null});
    assert.match(b.messages.find(m=>m.type==='streamlit:setComponentValue').value.warning,/unavailable or invalid/);
  }
});
test('quota failure reports that the latest changes are not saved',()=>{
  const b=browser('{}',false,true);b.render({profile:{settings:{name:'New'}}});
  assert.match(b.messages.at(-2).value.warning,/full or disabled/);
});
