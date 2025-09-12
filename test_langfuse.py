#!/usr/bin/env python3
"""
Test Langfuse Connection and Trace Creation
"""
import os
from dotenv import load_dotenv
from langfuse import Langfuse

# Load environment variables
load_dotenv()

def test_langfuse_connection():
    """Test basic Langfuse connection and trace creation"""
    print("🔍 Testing Langfuse Connection...")
    
    # Get configuration
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://staffer-langfuse-staging.fly.dev")
    
    print(f"Host: {host}")
    print(f"Public Key: {public_key[:20]}...")
    print(f"Secret Key: {secret_key[:20]}...")
    
    # Initialize Langfuse client
    lf = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host
    )
    
    print("✅ Langfuse client initialized")
    
    # Create a simple trace
    print("📝 Creating test trace...")
    
    with lf.start_as_current_observation(
        as_type='span',
        name="test_trace",
        input={"test": "data"},
        metadata={"environment": "test"}
    ) as span:
        # Update the trace
        lf.update_current_trace(
            output={"result": "success"},
            tags=["test", "debug"]
        )
        
        # Create an event
        lf.create_event(
            name="test_event",
            input={"event": "test"},
            output={"status": "completed"}
        )
        
        print("✅ Trace and event created")
    
    # Flush to ensure data is sent
    lf.flush()
    print("✅ Data flushed to Langfuse")
    
    return True

if __name__ == "__main__":
    try:
        test_langfuse_connection()
        print("🎉 Langfuse test completed successfully!")
    except Exception as e:
        print(f"❌ Langfuse test failed: {e}")
        import traceback
        traceback.print_exc()
