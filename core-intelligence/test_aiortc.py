import asyncio
from aiortc import RTCPeerConnection, RTCIceCandidate

async def test():
    pc = RTCPeerConnection()
    try:
        # Test if it accepts a string
        await pc.addIceCandidate("candidate:0 1 UDP 2122252543 192.168.1.5 59617 typ host")
        print("Accepted string")
    except Exception as e:
        print(f"Failed with string: {type(e).__name__}: {e}")

    try:
        # Test with object
        candidate = RTCIceCandidate(
            candidate="candidate:0 1 UDP 2122252543 192.168.1.5 59617 typ host",
            sdpMid="0",
            sdpMLineIndex=0
        )
        await pc.addIceCandidate(candidate)
        print("Accepted object")
    except Exception as e:
        print(f"Failed with object: {type(e).__name__}: {e}")
    
    await pc.close()

if __name__ == "__main__":
    asyncio.run(test())
