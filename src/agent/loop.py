import asyncio
from src.agent.understand import understand_engine
from src.agent.act import dispatcher
from src.core.contracts import Platform
from src.core.logger import log
from src.memory.storage import storage

class AutonomyLoop:
    def __init__(self):
        self.running = False

    async def run(self):
        self.running = True
        log.info("Starting REAL Autonomy OODA Loop...")
        while self.running:
            try:
                await self.tick()
            except Exception as e:
                log.error(f"Loop error: {e}")
            await asyncio.sleep(5) # Poll every 5 seconds for rapid MVP execution

    async def tick(self):
        # 1. Sense: Read from SQLite pending events
        event = await storage.fetch_next_event()
        if not event:
            return  # Sleep naturally

        event_id = event["id"]
        event_type = event["event_type"]
        payload = event["payload"]

        log.info(f"[Autonomy Loop] TICK: Processing event {event_id} of type {event_type}")
        
        # 2. Understand: Extract classification via Vertex AI GenAI SDK (Gemini 3 Flash in global region)
        # Assuming payload has a 'text' or 'message' field based on Meta/Reddit webhooks. 
        # Using a raw dump for the context engine to decipher if structure is complex.
        content_to_analyze = str(payload.get("text", payload)) 
        
        try:
            classification = understand_engine.classify(content_to_analyze)
            log.info(f"Classified event {event_id}: {classification.intent} ({classification.urgency})")
            
            # 3. Decide & Act
            # Currently acting only if complaint/urgent as an MVP test, to avoid spam
            if classification.intent == "complaint" or classification.urgency == "high":
                log.info(f"Targeting action for urgent event {event_id}...")
                
                # Logic to determine platform from event_type
                target_platform = None
                target_ref = "unknown"
                if "meta" in event_type:
                    target_platform = Platform.FACEBOOK
                    target_ref = payload.get("entry", [{}])[0].get("id", "test_id")
                elif "reddit" in event_type:
                    target_platform = Platform.REDDIT
                    target_ref = payload.get("name", "test_id")
                else:
                    target_platform = Platform.X

                # Example real call (Uncommenting the dispatcher as it has safe policies)
                # Reply explicitly mentioning ByteSocialAgent to differentiate from cloud run bot
                reply_text = "Hello! ByteSocialAgent here. We have logged your urgent request and a human will look into it."
                res = await dispatcher.execute_reply(target_platform, target_ref, reply_text)
                if not res.ok:
                    log.error(f"Action failed for {event_id}: {res.error}")
                    await storage.save_to_dlq(event_id, event_type, payload, f"Act failed: {res.error}")
            else:
                log.info(f"Event {event_id} ignored (Policy: intent={classification.intent}).")
                
            # Acknowledge and remove from queue
            await storage.delete_event(event_id)
            
        except Exception as e:
            log.error(f"Failed to process event {event_id}: {e}")
            await storage.save_to_dlq(event_id, event_type, payload, str(e))
            await storage.delete_event(event_id)

autonomy_loop = AutonomyLoop()
