import os
import razorpay

# Initialize Razorpay client
# Using a fallback mock for development if env vars are missing
def get_razorpay_client():
    key_id = os.getenv("RAZORPAY_KEY_ID", "mock_key_id")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "mock_key_secret")
    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        return client
    except Exception as e:
        print(f"Error initializing Razorpay client: {e}")
        return None

def create_order(amount_in_cents, currency="USD", receipt=None):
    """
    Creates a Razorpay order. Amount should be in smallest currency unit (e.g. cents).
    """
    client = get_razorpay_client()
    if not client:
        return None

    data = {
        "amount": amount_in_cents,
        "currency": currency,
        "receipt": receipt,
        "payment_capture": "1" # Auto capture
    }

    try:
        order = client.order.create(data=data)
        return order
    except Exception as e:
        print(f"Error creating Razorpay order: {e}")
        return None

def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Verifies the payment signature returned by Razorpay.
    """
    client = get_razorpay_client()
    if not client:
        return False

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        # Returns None on success, raises SignatureVerificationError on failure
        client.utility.verify_payment_signature(params_dict)
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception as e:
        print(f"Error verifying signature: {e}")
        return False
