"""
Image upload service for handling photo uploads to Supabase Storage.
"""
from config.storage import storage
from datetime import datetime
import uuid
from typing import Optional

class ImageService:
    """Service for handling image uploads."""
    
    @staticmethod
    def upload_shop_cnic_front(
        shop_id: int,
        order_booker_id: int,
        base64_image: str
    ) -> Optional[str]:
        """
        Upload shop owner CNIC front photo.
        
        Returns:
            Public URL of uploaded image or None
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shop_{shop_id}_cnic_front_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = f"cnic/front/{filename}"
        
        return storage.upload_base64_image(
            bucket_name="shop-registrations",
            file_path=file_path,
            base64_string=base64_image,
            content_type="image/jpeg"
        )
    
    @staticmethod
    def upload_shop_cnic_back(
        shop_id: int,
        order_booker_id: int,
        base64_image: str
    ) -> Optional[str]:
        """
        Upload shop owner CNIC back photo.
        
        Returns:
            Public URL of uploaded image or None
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shop_{shop_id}_cnic_back_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = f"cnic/back/{filename}"
        
        return storage.upload_base64_image(
            bucket_name="shop-registrations",
            file_path=file_path,
            base64_string=base64_image,
            content_type="image/jpeg"
        )
    
    @staticmethod
    def upload_shop_exterior(
        shop_id: int,
        order_booker_id: int,
        base64_image: str
    ) -> Optional[str]:
        """Upload shop exterior photo."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shop_{shop_id}_exterior_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = f"exterior/{filename}"
        
        return storage.upload_base64_image(
            bucket_name="shop-registrations",
            file_path=file_path,
            base64_string=base64_image,
            content_type="image/jpeg"
        )
    
    @staticmethod
    def upload_shop_owner_photo(
        shop_id: int,
        order_booker_id: int,
        base64_image: str
    ) -> Optional[str]:
        """Upload shop owner photo."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shop_{shop_id}_owner_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = f"owner/{filename}"
        
        return storage.upload_base64_image(
            bucket_name="shop-registrations",
            file_path=file_path,
            base64_string=base64_image,
            content_type="image/jpeg"
        )
    
    @staticmethod
    def upload_shop_visit_photo(
        visit_id: int,
        order_booker_id: int = None,
        delivery_man_id: int = None,
        base64_image: str = None
    ) -> Optional[str]:
        """
        Upload shop visit photo.
        
        Args:
            visit_id: Visit ID
            order_booker_id: Order booker ID (if visit by order booker)
            delivery_man_id: Delivery man ID (if visit by delivery man)
            base64_image: Base64 encoded image string
        
        Returns:
            Public URL of uploaded image or None
        """
        if not base64_image:
            return None
            
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        visitor_type = "ob" if order_booker_id else "dm"
        visitor_id = order_booker_id if order_booker_id else delivery_man_id
        filename = f"visit_{visit_id}_{visitor_type}_{visitor_id}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = f"visits/{filename}"
        
        return storage.upload_base64_image(
            bucket_name="shop-visits",
            file_path=file_path,
            base64_string=base64_image,
            content_type="image/jpeg"
        )
    
    @staticmethod
    def upload_delivery_photo(
        delivery_id: int,
        delivery_man_id: int,
        base64_image: str
    ) -> Optional[str]:
        """Upload delivery proof photo."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"delivery_{delivery_id}_dm_{delivery_man_id}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = f"proofs/{filename}"
        
        return storage.upload_base64_image(
            bucket_name="deliveries",
            file_path=file_path,
            base64_string=base64_image,
            content_type="image/jpeg"
        )
    
    @staticmethod
    def upload_collection_photo(
        collection_id: int,
        delivery_man_id: int,
        base64_image: str
    ) -> Optional[str]:
        """Upload daily collection proof photo."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collection_{collection_id}_dm_{delivery_man_id}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = f"proofs/{filename}"
        
        return storage.upload_base64_image(
            bucket_name="daily-collections",
            file_path=file_path,
            base64_string=base64_image,
            content_type="image/jpeg"
        )
    
    @staticmethod
    def delete_image_from_url(url: str) -> bool:
        """
        Delete image by extracting bucket and path from URL.
        
        URL format: http://127.0.0.1:54321/storage/v1/object/public/{bucket}/{path}
        """
        try:
            # Parse URL to get bucket and path
            parts = url.split("/storage/v1/object/public/")
            if len(parts) != 2:
                return False
            
            bucket_and_path = parts[1]
            bucket_name = bucket_and_path.split("/")[0]
            file_path = "/".join(bucket_and_path.split("/")[1:])
            
            return storage.delete_image(bucket_name, file_path)
        except Exception as e:
            print(f"Error deleting image from URL: {e}")
            return False

