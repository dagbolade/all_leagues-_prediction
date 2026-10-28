// Public rendered match pages only. No data API calls.
export function createCollector(fs, outRoot) {
const readOn = async(tab)=>tab.playwright.evaluate(()=>({source:location.href,title:document.title,breadcrumb:Array.from(document.querySelectorAll('ul.breadcrumb li')).map(n=>n.innerText),team:document.querySelector('input[name="team"]:checked')?.value,teams:Array.from(document.querySelectorAll('label[for="team-home"],label[for="team-away"]')).map(n=>n.innerText),headers:Array.from(document.querySelectorAll('#match-rosters thead th')).map(n=>n.innerText),rows:Array.from(document.querySelectorAll('#match-rosters tbody tr')).filter(r=>r.querySelector('a[href*="player/"]')).map(r=>({player_url:r.querySelector('a[href*="player/"]').href,cells:Array.from(r.cells).map(c=>c.innerText)})),cards:Array.from(document.querySelectorAll('.timeline-group')).filter(n=>n.querySelector('[title*="card"],[title*="Card"]')).map(n=>({player_url:n.querySelector('a[href*="player/"]')?.href,titles:Array.from(n.querySelectorAll('[title*="card"],[title*="Card"]')).map(i=>i.getAttribute('title'))}))}));
const collectOn = async(tab,item)=>{await tab.goto(item.url);await tab.playwright.locator('#match-rosters table').waitFor({state:'visible',timeoutMs:12000});var home=await readOn(tab);if(home.team!=='h')throw Error('Unexpected initial roster');var away;for(var attempt=0;attempt<3;attempt++){await tab.playwright.locator('label[for="team-away"]').click();away=await readOn(tab);if(away.team==='a'&&away.rows[0]?.player_url!==home.rows[0]?.player_url)break;await tab.getAXState({emit:false});}if(home.source!==item.url||away.source!==item.url||home.team!=='h'||away.team!=='a'||home.rows.length<11||away.rows.length<11||home.rows[0].player_url===away.rows[0].player_url)throw Error('Roster not ready or incomplete');await fs.writeFile(outRoot+'/matches/'+item.url.split('/').at(-1)+'.json',JSON.stringify({observed_at:new Date().toISOString(),league:item.league,home,away}));};
return collectOn;
}

export async function collectBatch(tabs, fs, outRoot, matches, cursor=0, budgetMs=35000) {
 const collect=createCollector(fs,outRoot); const start=Date.now(); const failures=[];
 await fs.mkdir(outRoot+"/matches",{recursive:true});
 while(cursor<matches.length && Date.now()-start<budgetMs) {
  const batch=matches.slice(cursor,cursor+tabs.length);
  await Promise.all(batch.map(async(item,i)=>{try {await collect(tabs[i],item);} catch(e){failures.push({...item,error:String(e)});}}));
  cursor+=batch.length;
 }
 const result={cursor,total:matches.length,failures};
 await fs.writeFile(outRoot+"/batch-"+cursor+".json",JSON.stringify(result));
 return result;
}
