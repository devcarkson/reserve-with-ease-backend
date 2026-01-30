import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/messaging/1/?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY5NzczNTMxLCJpYXQiOjE3Njk3Njk5MzEsImp0aSI6ImE3YTdkNWE3NzQ3MDRlMDZiZDE1YzlkOWMyNDg2OWIwIiwidXNlcl9pZCI6IjM3In0.Wb5-qrK8vSaQi2Qt4spr7kK-mJwnvb0GQWuhoaiBhdw"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            
            # Send a test message
            await websocket.send(json.dumps({
                "type": "send_message",
                "content": "Test message from Python"
            }))
            
            # Listen for responses
            response = await websocket.recv()
            print(f"Received: {response}")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())