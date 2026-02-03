"""
Index Travel Policies into Pinecone
Run this once to populate the vector database
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.rag_service import get_rag_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PolicyIndexer")

# Policy documents
POLICIES = {
    "cancellation": """
# Cancellation Policy

## Flight Cancellation
- **Free cancellation**: Up to 24 hours before departure for most fare classes
- **Business/First Class**: Full refund up to 12 hours before departure
- **Economy Flex**: Refund available up to 6 hours before departure (10% fee)
- **Economy Basic**: Non-refundable, but date change allowed (€50 fee)
- **Last minute cancellation**: Less than 24 hours - 50% penalty applies

## Hotel Cancellation
- **Standard booking**: Free cancellation up to 48 hours before check-in
- **Non-refundable rates**: No cancellation allowed, but modification possible with 20% fee
- **Peak season**: 72 hours cancellation notice required
- **No-show**: Full charge applies

## Refund Processing Time
- Credit card refunds: 7-14 business days
- Bank transfers: 3-5 business days
- Voucher refunds: Instant
    """,
    
    "baggage": """
# Baggage Policy

## Checked Baggage
**Economy Class:**
- 1 piece up to 23kg (50 lbs)
- Dimensions: 158cm (62 inches) total (length + width + height)
- Additional bags: €50 per piece

**Business/First Class:**
- 2 pieces up to 32kg (70 lbs) each
- Priority baggage handling
- Free additional bag for loyalty members

## Carry-on Baggage
- 1 cabin bag: 55x40x20cm, max 8kg
- 1 personal item: Laptop bag, purse, or small backpack
- Must fit in overhead bin or under seat

## Special Items
- Sports equipment: €75 per item
- Musical instruments: Free if fits in cabin
- Medical equipment: Free, no weight limit
- Pets: €100-150 depending on size

## Excess Baggage Fees
- 0-5kg over: €25
- 5-10kg over: €50
- 10kg+ over: €100
    """,
    
    "checkin": """
# Check-in Policy

## Online Check-in
- Available 24-48 hours before departure
- Mobile boarding pass available
- Seat selection included
- Baggage drop-off required at airport

## Airport Check-in
- International flights: 3 hours before departure
- Domestic flights: 2 hours before departure
- Counter closes 60 minutes before departure

## Late Check-in
- 45-60 minutes before departure: Subject to availability
- Less than 45 minutes: Likely denied boarding
- No refund for missed flights due to late check-in
    """,
    
    "payment": """
# Payment Policy

## Accepted Payment Methods
- Credit cards: Visa, Mastercard, American Express
- Debit cards: Most major banks
- PayPal, Apple Pay, Google Pay
- Bank transfers (for bookings over €1000)
- Travel vouchers and gift cards

## Payment Security
- PCI DSS compliant
- 3D Secure authentication
- No card details stored
- Encrypted transactions

## Currency
- Base currency: EUR
- Automatic conversion available
- Exchange rate updated daily
- No hidden fees

## Payment Plans
- Full payment required for Economy
- Business/First Class: 50% deposit, balance 14 days before travel
- Group bookings (10+): Custom payment terms available
    """,
    
    "modification": """
# Modification Policy

## Date Changes
**Flight Date Change:**
- Up to 7 days before: €50 fee + fare difference
- 3-7 days before: €100 fee + fare difference  
- Less than 3 days: €150 fee + fare difference

**Hotel Date Change:**
- Up to 7 days before check-in: Free
- 3-7 days before: €25 fee
- Less than 3 days: Subject to availability

## Name Changes
- Minor corrections (typos): Free within 24 hours of booking
- Full name change: €100 fee (if airline permits)
- Some fare classes don't allow name changes

## Route Changes
- Domestic to domestic: €75 fee + fare difference
- International route change: €150 fee + fare difference
- Downgrade: Difference refunded minus €50 admin fee
    """,
    
    "special_assistance": """
# Special Assistance

## Passengers with Disabilities
- Wheelchair assistance: Free, request 48 hours in advance
- Priority boarding available
- Service animals: Free, documentation required
- Medical equipment: Free carry-on allowance

## Traveling with Children
- Infants (under 2): 10% of adult fare, lap seating
- Children (2-11): Usually 25-30% discount
- Unaccompanied minors: €50 supervision fee
- Strollers: Free gate check

## Medical Conditions
- Oxygen provision: €100 per flight segment, pre-approval required
- Special meals: Free, request 48 hours in advance (diabetic, allergic, religious)
- Stretcher service: Requires booking 3 seats, advance notice
    """
}


def main():
    """Index all policies into Pinecone"""
    logger.info("🚀 Starting policy indexing...")
    
    # Get RAG service
    rag = get_rag_service()
    
    if not rag._initialized:
        logger.error("❌ RAG Service failed to initialize")
        return False
    
    # Prepare documents and metadata
    documents = []
    metadatas = []
    
    for policy_type, content in POLICIES.items():
        documents.append(content)
        metadatas.append({
            "policy_type": policy_type,
            "source": "official_policy",
            "language": "en"
        })
    
    # Index documents
    success = rag.index_documents(documents, metadatas)
    
    if success:
        logger.info("✅ All policies indexed successfully!")
        logger.info(f"📊 Total policies: {len(POLICIES)}")
        logger.info(f"📝 Policy types: {', '.join(POLICIES.keys())}")
        
        # Test search
        logger.info("\n🧪 Testing search...")
        test_query = "What is the baggage allowance?"
        results = rag.search(test_query, top_k=2)
        logger.info(f"Query: {test_query}")
        logger.info(f"Results: {len(results)} chunks found")
        if results:
            logger.info(f"Top result relevance: {results[0]['relevance_score']:.4f}")
        
        return True
    else:
        logger.error("❌ Indexing failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)