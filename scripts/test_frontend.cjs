const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch();const page=await browser.newPage();
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:3000');
 await page.screenshot({path:'artifacts/develop-input.png',fullPage:true});
 await page.getByRole('button',{name:'Analisar',exact:true}).click();
 await page.locator('.form-feedback.error').waitFor();
 await page.locator('.cm-content').fill('OPENQASM 2.0; include "qelib1.inc"; qreg q[1]; h q[0]; h q[0];');
 await page.getByRole('button',{name:'Analisar',exact:true}).click();
 await page.getByText('Equivalência: confirmada.',{exact:false}).waitFor();
 await page.getByRole('button',{name:'Voltar ao editor',exact:true}).click();
 await page.locator('.cm-content').fill('invalido');
 await page.getByRole('button',{name:'Analisar',exact:true}).click();
 await page.getByText('Código inválido',{exact:true}).waitFor();
 await page.getByRole('button',{name:'Voltar ao editor',exact:true}).click();
 await page.getByRole('button',{name:'Limpar tudo',exact:true}).click();
 await page.locator('#analysis-question').fill('Explique em duas frases para que serve a transpilação no Qiskit.');
 await page.locator('#top-k').selectOption('8');
 if(process.env.SKIP_LIVE_LLM==='1'){
  await page.route('**/api/query',r=>{
   assert.equal(r.request().postDataJSON().web_search,true);
   return r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
    response:'Resposta controlada de teste [Web 1]',status:'ok',request_id:'teste',web_status:'used',
    search_suggestions_html:'<p>Pesquisa Google de teste</p>',sources:[{document_id:'web_1',chunk_id:'web_1',source:'https://example.org',title:'Fonte de teste',content:'Evidência controlada',origin:'web',retrieved_at:'2026-11-13T00:00:00Z'}]
   })});
  });
 }
 await page.getByRole('button',{name:'Analisar',exact:true}).click();
 await page.getByRole('region',{name:'Resultado'}).waitFor({timeout:120000});
 await page.getByRole('button',{name:/Ver fonte 1/}).click();
 await page.getByRole('dialog').waitFor();await page.keyboard.press('Escape');
 if(process.env.SKIP_LIVE_LLM==='1'){
  assert.equal(await page.locator('iframe').getAttribute('sandbox'),'allow-popups allow-popups-to-escape-sandbox');
  await page.unroute('**/api/query');
 }
 await page.screenshot({path:'artifacts/develop-results.png',fullPage:true});
 await page.getByRole('button',{name:'Voltar ao editor',exact:true}).click();
 await page.route('**/api/query',r=>r.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'Falha controlada',request_id:'teste'})}));
 await page.getByRole('button',{name:'Analisar',exact:true}).click();await page.getByText('Falha no serviço',{exact:true}).waitFor();
 await page.unroute('**/api/query');
 await page.route('**/api/query',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({response:'Sem fontes',sources:[],status:'insufficient_context',request_id:'teste'})}));
 await page.getByRole('button',{name:'Tentar novamente',exact:true}).click();await page.getByRole('heading',{name:'Evidências insuficientes',exact:true}).waitFor();
 await page.getByRole('button',{name:'Voltar ao editor',exact:true}).click();await page.unroute('**/api/query');
 await page.route('**/api/query',async r=>{await new Promise(ok=>setTimeout(ok,1500));await r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({response:'late',sources:[],status:'ok',request_id:'teste'})}).catch(()=>{});});
 await page.getByRole('button',{name:'Analisar',exact:true}).click();
 await page.getByRole('button',{name:/Voltar para editar/}).click();
 await page.waitForTimeout(1700);await page.getByRole('heading',{name:'Nova análise',exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await page.screenshot({path:'artifacts/develop-mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);
 console.log('PASS: entrada, Qiskit real, LLM conforme SKIP_LIVE_LLM, top_k, fonte/ESC, erro QASM, falha/retry, evidencia insuficiente, cancelamento e mobile');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
