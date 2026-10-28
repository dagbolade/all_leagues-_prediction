// Run from the Codex browser REPL with a bound Understat tab and fs/promises.
// Uses only visible DOM tables and normal pagination clicks; no data API calls.
export async function collectPlayer(tab, fs, source, output) {
  if (!/^https:\/\/understat\.com\/player\/\d+$/.test(source)) throw Error('Invalid player URL');
  await tab.goto(source);
  await tab.playwright.locator('#player-history table').waitFor({state:'visible',timeoutMs:15000});
  const pages=[];
  for(let attempt=0;attempt<200;attempt++) {
    const page=await tab.playwright.evaluate(()=>({
      player:document.querySelector('h1').innerText,source:location.href,
      headers:Array.from(document.querySelectorAll('#player-history thead th')).map(n=>n.innerText),
      rows:Array.from(document.querySelectorAll('#player-history tbody tr'))
        .filter(r=>r.querySelector('a[href*="match/"]'))
        .map(r=>({match_url:r.querySelector('a[href*="match/"]').href,cells:Array.from(r.cells).map(c=>c.innerText)})),
      page:document.querySelector('#player-history + .table-control-panel .current').getAttribute('data-page'),
      next:!document.querySelector('#player-history + .table-control-panel .prevNext:last-child').classList.contains('disabled')
    }));
    if(page.source!==source || !page.rows.length)throw Error('Unexpected or empty player page');
    const previous=pages.at(-1);
    if(previous?.page===page.page) {
      if(JSON.stringify(previous)!==JSON.stringify(page))throw Error('Page changed during extraction');
    } else {
      if(Number(page.page)!==pages.length+1)throw Error('Pagination gap');
      pages.push(page);
    }
    if(!page.next) {
      await fs.writeFile(output,JSON.stringify({observed_at:new Date().toISOString(),pages},null,2));
      return {player:page.player,appearances:pages.reduce((n,p)=>n+p.rows.length,0)};
    }
    await tab.playwright.locator('#player-history + .table-control-panel .page:not(.prevNext)')
      .filter({hasText:new RegExp('^'+(Number(page.page)+1)+'$')}).click();
  }
  throw Error('Pagination limit reached; incomplete history not saved');
}
