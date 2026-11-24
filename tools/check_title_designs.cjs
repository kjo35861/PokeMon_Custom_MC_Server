// Logic check for the review-only fragment. This is not a browser render test.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const rootDir=process.argv[2]?path.resolve(process.argv[2]):path.resolve(__dirname,'../docs/design/legendary-titles');
const rows=JSON.parse(fs.readFileSync(path.join(rootDir,'preview-data.json'),'utf8'));
class Element {
  constructor(){this.children=[];this.style={};this.dataset={};this.attrs={};this.listeners={};}
  append(...children){this.children.push(...children);}
  setAttribute(key,value){this.attrs[key]=value;}
  addEventListener(key,handler){this.listeners[key]=handler;}
  querySelector(selector){return selector==='img'?this.children.flatMap(c=>c.children||[]).find(c=>c.tag==='img'):elements[selector.slice(1)];}
  querySelectorAll(){return [...elements['pm-legend-grid'].children,...elements['pm-myth-grid'].children];}
}
const elements={};
for(const name of ['pm-title-review','pm-title-icon','pm-title-text','pm-title-species','pm-title-color','pm-title-chat','pm-title-design','pm-legend-grid','pm-myth-grid'])elements[name]=new Element();
let theme='dark';const window={addEventListener(){},matchMedia(){return {addEventListener(){}};}};
const context={window,document:{getElementById:id=>elements[id],createElement:tag=>Object.assign(new Element(),{tag}),documentElement:{}},getComputedStyle:()=>({color:theme==='dark'?'rgb(230, 230, 230)':'rgb(30, 30, 30)'}),MutationObserver:class{observe(){}}};
const source=fs.readFileSync(path.join(rootDir,'preview.fragment.html'),'utf8').match(/<script>([\s\S]*?)<\/script>/)[1].replace('__POCKETMATE_TITLE_DATA__',JSON.stringify(rows));
vm.runInNewContext(source,context);
assert.equal(elements['pm-legend-grid'].children.length,71);assert.equal(elements['pm-myth-grid'].children.length,23);
const buttons=elements['pm-title-review'].querySelectorAll();
for(const mode of ['dark','light']){
  theme=mode;
  for(const row of rows){
    const button=buttons.find(b=>b.dataset.pmDex===row.dex);button.listeners.click();
    assert.equal(elements['pm-title-text'].textContent,row.title);
    assert.equal(elements['pm-title-species'].textContent,row.name);
    assert.equal(elements['pm-title-icon'].src,row[mode]);
    assert.equal(elements['pm-title-text'].style.color,'#'+(mode==='light'?row.lightColor:row.color));
    if(row.exterior_features)assert(elements['pm-title-design'].textContent.includes(row.exterior_features)&&elements['pm-title-design'].textContent.includes(row.title_relation));
    if(row.symbol_components)assert(elements['pm-title-design'].textContent.includes(row.symbol_components)&&elements['pm-title-design'].textContent.includes(row.title_relation));
    assert.equal(button.attrs['aria-pressed'],'true');
    assert.equal(buttons.filter(b=>b.attrs['aria-pressed']==='true').length,1);
  }
}
console.log('Review preview: 94 selections in both themes, selected icon/title/color and 71+23 grouping passed (188 cases).');
