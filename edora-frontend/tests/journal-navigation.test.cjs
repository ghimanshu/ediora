const test = require('node:test');
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/lib/journal-navigation.ts', 'utf8');
const context = { exports: {} };
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, context);
test('journal menus group policies once and retain top-level links and child order', () => {
  const result = context.exports.groupJournalMenu([
    {slug:'home',title:'Home'}, {slug:'ethics',title:'Policy',menu_group:'Ethics'},
    {slug:'contact-us',title:'Contact Us'}, {slug:'ai',title:'AI',menu_group:'Ethics'},
    {slug:'guidelines',title:'Guidelines',menu_group:'For Authors'}
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(result)).map(e=>[e.title,e.grouped,e.items.map(p=>p.slug)]), [
    ['Home',false,['home']], ['Ethics',true,['ethics','ai']], ['Contact Us',false,['contact-us']], ['For Authors',true,['guidelines']]
  ]);
});
