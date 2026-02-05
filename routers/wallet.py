"""
Wallet Router
=============
Handles wallet operations for distributors, order bookers, and delivery men.

API ENDPOINTS:
- GET /wallets/{user_type}/{user_id}/balance - Get wallet balance
- GET /wallets/{user_type}/{user_id}/transactions - Get transaction history
- POST /wallets/transfer - Transfer money between wallets (RESTRICTED: Only distributors can collect from order_bookers/delivery_men)
- GET /wallets/distributor/{distributor_id}/all-wallets - List all wallets of order bookers and delivery men (Distributor only)
- POST /wallets/distributor/{distributor_id}/collect - Collect money from order booker or delivery man (Distributor only)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, List
from config.database import get_db
from models.schemas import WalletTransferRequest, WalletCollectionRequest
from services.wallet_service import WalletService
from utils.auth_helpers import get_current_user_from_request
from utils.dependencies import get_current_distributor

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
    
    ⚠️ RESTRICTED: Only distributors can collect money from order bookers/delivery men.
    Order bookers and delivery men CANNOT initiate transfers to distributors.
    
    API: POST /wallets/transfer
    
    Request Body:
        {
            "from_user_type": "order_booker",
            "from_user_id": 1,
            "to_user_type": "distributor",
            "to_user_id": 1,
            "amount": 5000.00,
            "description": "Collection by distributor",
            "initiated_by_type": "distributor",
            "initiated_by_id": 1
        }
    
    Response:
        {
            "transfer_id": 123,
            "from_wallet": {...},
            "to_wallet": {...},
            "amount": 5000.00,
            "description": "Collection by distributor",
            "created_at": "2026-01-28T10:30:00"
        }
    """
    # Get current user from request to check authorization
    current_user = await get_current_user_from_request(request)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # RESTRICTION: Only allow transfers FROM order_booker/delivery_man TO distributor
    # AND only if initiated by a distributor
    if transfer.from_user_type not in ['order_booker', 'delivery_man']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Transfers can only be initiated FROM order_booker or delivery_man wallets"
        )
    
    if transfer.to_user_type != 'distributor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Transfers can only be made TO distributor wallets"
        )
    
    # Verify that the current user is a distributor and is the one receiving the money
    if current_user.get('user_role') != 'distributor':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only distributors can collect money from order bookers and delivery men"
        )
    
    # Verify the distributor is collecting to their own wallet
    if current_user.get('user_id') != transfer.to_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only collect money to your own wallet"
        )
    
    # Verify the order booker/delivery man belongs to this distributor
    if transfer.from_user_type == 'order_booker':
        from repositories.order_booker_repository import OrderBookerRepository
        order_booker = OrderBookerRepository.get_by_id(db, transfer.from_user_id)
        if not order_booker or order_booker.distributor_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This order booker does not belong to your distributor account"
            )
    elif transfer.from_user_type == 'delivery_man':
        from repositories.delivery_man_repository import DeliveryManRepository
        delivery_man = DeliveryManRepository.get_by_id(db, transfer.from_user_id)
        if not delivery_man or delivery_man.distributor_id != current_user.get('user_id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This delivery man does not belong to your distributor account"
            )
    
    if transfer.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer amount must be positive"
        )
    
    try:
        from decimal import Decimal
        # Override initiated_by to ensure it's the distributor
        result = WalletService.transfer_between_wallets(
            db=db,
            from_user_type=transfer.from_user_type,
            from_user_id=transfer.from_user_id,
            to_user_type=transfer.to_user_type,
            to_user_id=transfer.to_user_id,
            amount=Decimal(str(transfer.amount)),
            description=transfer.description or f"Collection by distributor from {transfer.from_user_type}",
            initiated_by_type='distributor',
            initiated_by_id=current_user.get('user_id'),
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


@router.get("/distributor/{distributor_id}/all-wallets")
async def list_all_wallets_for_distributor(
    distributor_id: int,
    current_distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    List all wallets of order bookers and delivery men under a distributor.
    
    ⚠️ RESTRICTED: Only the distributor can view their order bookers' and delivery men's wallets.
    
    API: GET /wallets/distributor/{distributor_id}/all-wallets
    
    Response:
        [
            {
                "wallet_id": 1,
                "user_type": "order_booker",
                "user_id": 1,
                "user_name": "John Doe",
                "current_balance": 5000.00,
                "is_active": true
            },
            ...
        ]
    """
    # Verify the distributor is viewing their own data
    if current_distributor.get('user_id') != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view wallets for your own distributor account"
        )
    
    try:
        wallets = WalletService.get_all_wallets_for_distributor(db, distributor_id)
        return wallets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching wallets: {str(e)}"
        )


@router.post("/distributor/{distributor_id}/collect")
async def collect_money_from_user(
    distributor_id: int,
    collection: WalletCollectionRequest,
    current_distributor: Dict = Depends(get_current_distributor),
    db: Session = Depends(get_db)
):
    """
    Collect money from an order booker or delivery man.
    
    ⚠️ RESTRICTED: Only distributors can collect money from their order bookers/delivery men.
    
    API: POST /wallets/distributor/{distributor_id}/collect
    
    Request Body:
        {
            "from_user_type": "order_booker",
            "from_user_id": 1,
            "amount": 5000.00,
            "description": "Collection from order booker",
            "metadata": {}
        }
    
    Response:
        {
            "transfer_id": 123,
            "from_wallet": {...},
            "to_wallet": {...},
            "amount": 5000.00,
            "description": "Collection from order booker",
            "created_at": "2026-01-28T10:30:00"
        }
    """
    # Verify the distributor is collecting to their own wallet
    if current_distributor.get('user_id') != distributor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only collect money to your own distributor account"
        )
    
    # Verify from_user_type is order_booker or delivery_man
    if collection.from_user_type not in ['order_booker', 'delivery_man']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only collect from order_booker or delivery_man"
        )
    
    # Verify the order booker/delivery man belongs to this distributor
    if collection.from_user_type == 'order_booker':
        from repositories.order_booker_repository import OrderBookerRepository
        order_booker = OrderBookerRepository.get_by_id(db, collection.from_user_id)
        if not order_booker or order_booker.distributor_id != distributor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This order booker does not belong to your distributor account"
            )
    elif collection.from_user_type == 'delivery_man':
        from repositories.delivery_man_repository import DeliveryManRepository
        delivery_man = DeliveryManRepository.get_by_id(db, collection.from_user_id)
        if not delivery_man or delivery_man.distributor_id != distributor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This delivery man does not belong to your distributor account"
            )
    
    if collection.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection amount must be positive"
        )
    
    try:
        from decimal import Decimal
        result = WalletService.transfer_between_wallets(
            db=db,
            from_user_type=collection.from_user_type,
            from_user_id=collection.from_user_id,
            to_user_type='distributor',
            to_user_id=distributor_id,
            amount=Decimal(str(collection.amount)),
            description=collection.description or f"Collection by distributor from {collection.from_user_type}",
            initiated_by_type='distributor',
            initiated_by_id=distributor_id,
            transaction_metadata=collection.metadata
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
            detail=f"Error processing collection: {str(e)}"
        )

