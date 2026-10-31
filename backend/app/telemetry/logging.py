import json
import logging
import time
from opentelemetry import trace, propagate
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"timestamp":time.time(),"level":record.levelname,"logger":record.name,"message":record.getMessage()})
class JSONSpanExporter(SpanExporter):
    def export(self,spans):
        for span in spans: logging.getLogger("traces").info(span.to_json(indent=None))
        return SpanExportResult.SUCCESS
    def shutdown(self): pass

def configure():
    handler=logging.StreamHandler(); handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=logging.INFO,handlers=[handler],force=True)
    if not isinstance(trace.get_tracer_provider(),TracerProvider):
        provider=TracerProvider(); provider.add_span_processor(SimpleSpanProcessor(JSONSpanExporter()))
        trace.set_tracer_provider(provider)

def instrument(app):
    @app.middleware("http")
    async def telemetry(request,call_next):
        execution_id=request.headers.get("x-execution-id","")
        with trace.get_tracer("failurelab.http").start_as_current_span(request.method+" "+request.url.path,context=propagate.extract(dict(request.headers))) as span:
            span.set_attribute("failurelab.execution_id",execution_id)
            response=await call_next(request)
            logging.getLogger("http").info(json.dumps({"execution_id":execution_id,"method":request.method,"path":request.url.path,"status":response.status_code,"trace_id":format(span.get_span_context().trace_id,"032x")}))
            return response
