import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(".."))

from aiortc import RTCPeerConnection
from shared.schemas.voice import SDPOffer, ICECandidate
from voice_handler import VoiceHandler

async def test_handshake():
    handler = VoiceHandler()
    
    # 1. Create client peer connection
    client_pc = RTCPeerConnection()
    
    # Add an audio transceiver to generate a valid offer for audio
    client_pc.addTransceiver("audio", direction="sendrecv")
    
    # 2. Generate offer
    offer = await client_pc.createOffer()
    await client_pc.setLocalDescription(offer)
    
    # 3. Simulate calling /voice/offer
    print("Testing create_session...")
    session_id, sdp_answer = await handler.create_session(
        SDPOffer(type=offer.type, sdp=offer.sdp)
    )
    
    print(f"Session created: {session_id}")
    print(f"Answer contains ICE candidates: {'a=candidate' in sdp_answer.sdp}")
    assert 'a=candidate' in sdp_answer.sdp, "SDP Answer does not contain ICE candidates! Waiting logic failed."
    
    # 4. Simulate sending an ICE candidate to /voice/ice-candidate
    print("Testing add_ice_candidate...")
    mock_candidate = ICECandidate(
        candidate="candidate:0 1 UDP 2122252543 192.168.1.5 59617 typ host",
        sdpMid="0",
        sdpMLineIndex=0
    )
    
    try:
        await handler.add_ice_candidate(session_id, mock_candidate)
        print("ICE candidate added successfully without AttributeError.")
    except Exception as e:
        print(f"FAILED to add ICE candidate: {type(e).__name__}: {e}")
        assert False, "add_ice_candidate failed"
        
    print("All tests passed successfully.")
    
    await client_pc.close()
    await handler.close_all()

if __name__ == "__main__":
    asyncio.run(test_handshake())
