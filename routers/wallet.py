"""
Wallet Router
=============
Handles wallet operations for distributors, order bookers, and delivery men.

API ENDPOINTS:
- GET /wallets/{user_type}/{user_id}/balance - Get wallet balance
- GET /wallets/{user_type}/{user_id}/transactions - Get transaction history
- POST /wallets/transfer - Transfer money between wallets
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict
from config.database import get_db
from models.schemas import WalletTransferRequest
from services.wallet_service import WalletService
from utils.auth_helpers import get_current_user_from_request

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.get("/{user_type}/{user_id}/balance")
async def get_wallet_balance(
    user_type: str,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get wallet balance for a user.
    
    API: GET /wallets/{user_type}/{user_id}/balance
    
    Path Parameters:
        user_type: Type of user ('distributor', 'order_booker', 'delivery_man')
        user_id: ID of the user
    
    Response:
        {
            "wallet_id": 1,
            "user_type": "order_booker",
            "user_id": 1,
            "current_balance": 5000.00,
            "is_active": true
        }
    """
    if user_type not in ['distributor', 'order_booker', 'delivery_man']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_type. Must be 'distributor', 'order_booker', or 'delivery_man'"
        )
    
    try:
        balance = WalletService.get_wallet_balance(db, user_type, user_id)
        return balance
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching wallet balance: {str(e)}"
        )


@router.get("/{user_type}/{user_id}/transactions")
async def get_transaction_history(
    user_type: str,
    user_id: int,
    limit: int = 100,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get transaction history for a wallet.
    
    API: GET /wallets/{user_type}/{user_id}/transactions?limit=100
    
    Path Parameters:
        user_type: Type of user ('distributor', 'order_booker', 'delivery_man')
        user_id: ID of the user
    
    Query Parameters:
        limit: Maximum number of transactions to return (default: 100)
    
    Response:
        [
            {
                "id": 1,
                "transaction_type": "credit",
                "amount": 5000.00,
                "balance_before": 0.00,
                "balance_after": 5000.00,
                "description": "Collection approved from shop ABC",
                "reference_type": "daily_collection",
                "reference_id": 123,
                "initiated_by_type": "distributor",
                "initiated_by_id": 1,
                "created_at": "2026-01-28T10:30:00"
            },
            ...
        ]
    """
    if user_type not in ['distributor', 'order_booker', 'delivery_man']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user_type. Must be 'distributor', 'order_booker', or 'delivery_man'"
        )
    
    if limit < 1 or limit > 1000:
        limit = 100
    
    try:
        transactions = WalletService.get_transaction_history(db, user_type, user_id, limit)
        return transactions
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error fetching transaction history for {user_type} {user_id}: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching transaction history: {str(e)}"
        )


@router.post("/transfer")
async def transfer_between_wallets(
    transfer: WalletTransferRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Transfer money from one wallet to another.
    
    API: POST /wallets/transfer
    
    Request Body:
        {
            "from_user_type": "order_booker",
            "from_user_id": 1,
            "to_user_type": "distributor",
            "to_user_id": 1,
            "amount": 5000.00,
            "description": "Transfer collected money to distributor"
        }
    
    Response:
        {
            "transfer_id": 123,
            "from_wallet": {
                "wallet_id": 1,
                "user_type": "order_booker",
                "user_id": 1,
                "balance_before": 10000.00,
                "balance_after": 5000.00,
                "transaction_id": 456
            },
            "to_wallet": {
                "wallet_id": 2,
                "user_type": "distributor",
                "user_id": 1,
                "balance_before": 0.00,
                "balance_after": 5000.00,
                "transaction_id": 457
            },
            "amount": 5000.00,
            "description": "Transfer collected money to distributor",
            "created_at": "2026-01-28T10:30:00"
        }
    """
    if transfer.from_user_type not in ['distributor', 'order_booker', 'delivery_man']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid from_user_type. Must be 'distributor', 'order_booker', or 'delivery_man'"
        )
    
    if transfer.to_user_type not in ['distributor', 'order_booker', 'delivery_man']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid to_user_type. Must be 'distributor', 'order_booker', or 'delivery_man'"
        )
    
    if transfer.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer amount must be positive"
        )
    
    try:
        from decimal import Decimal
        result = WalletService.transfer_between_wallets(
            db=db,
            from_user_type=transfer.from_user_type,
            from_user_id=transfer.from_user_id,
            to_user_type=transfer.to_user_type,
            to_user_id=transfer.to_user_id,
            amount=Decimal(str(transfer.amount)),
            description=transfer.description,
            initiated_by_type=transfer.initiated_by_type,
            initiated_by_id=transfer.initiated_by_id,
            transaction_metadata=transfer.metadata
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing transfer: {str(e)}"
        )

