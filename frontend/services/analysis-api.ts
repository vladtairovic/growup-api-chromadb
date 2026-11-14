export type AnalysisRequest={question:string;code:string;backend:string;top_k?:number;web_search?:boolean};
export type Source={document_id:string;chunk_id:string;source:string;content:string;origin?:'local'|'web';title?:string;retrieved_at?:string};
export type QuantumResult={original:{profundidade:number;total_operacoes:number};proposta:{profundidade:number;total_operacoes:number};equivalente:boolean|null;motivo:string|null;circuito_otimizado_qasm:string};
export type AnalysisResponse={request_id:string;status:string;answer:string;sources:Source[];quantum?:QuantumResult;warnings:string[];web_status?:string;search_suggestions_html?:string|null};
export class AnalysisError extends Error {constructor(message:string,public status:number,public requestId?:string){super(message);}}
async function post<T>(path:string,body:unknown,signal?:AbortSignal):Promise<{data:T;id:string}> {
 const res=await fetch("/api"+path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body),signal});
 const data=await res.json().catch(()=>null);
 if(!res.ok)throw new AnalysisError(data?.message||"Serviço indisponível.",res.status,data?.request_id);
 if(!data)throw new AnalysisError("Resposta inválida do serviço.",502);
 return {data,id:res.headers.get("x-request-id")||""};
}
export async function submitAnalysis(payload:AnalysisRequest,signal?:AbortSignal):Promise<AnalysisResponse>{
 if(payload.backend!=="reference")throw new AnalysisError("Backend não suportado.",422);
 if(payload.code.length>10000||payload.question.length+payload.code.length>29000)throw new AnalysisError("Entrada excede o limite permitido.",422);
 const result:AnalysisResponse={request_id:"",status:"ok",answer:"",sources:[],warnings:[]};
 if(payload.code.trim()){
 const q=await post<QuantumResult>("/qiskit/optimize",{qasm:payload.code,optimization_level:3},signal);
 result.quantum=q.data;result.request_id=q.id;
 }
 if(payload.question.trim()){
 try{
 const r=await post<{response:string;sources:Source[];status:string;request_id:string;warnings?:string[];web_status?:string;search_suggestions_html?:string|null}>("/query",{input:payload.question+(payload.code?"\n\nCircuito enviado:\n"+payload.code:""),top_k:payload.top_k||5,web_search:payload.web_search??true},signal);
 result.answer=r.data.response;result.sources=r.data.sources;result.request_id=r.data.request_id;
 result.status=r.data.status;result.warnings.push(...(r.data.warnings||[]));result.web_status=r.data.web_status;result.search_suggestions_html=r.data.search_suggestions_html;
 if(result.quantum&&result.status==="insufficient_context"){result.status="partial";result.warnings.push("Sem evidência documental suficiente. As métricas Qiskit continuam disponíveis.");}
 }catch(e){if(signal?.aborted||!result.quantum)throw e;result.status="partial";result.warnings.push("A explicação não pôde ser obtida. "+(e as Error).message);}
 }else if(result.quantum){result.answer="Circuito processado pelo Qiskit. As métricas abaixo foram calculadas sobre o circuito enviado."; }
 return result;
}
