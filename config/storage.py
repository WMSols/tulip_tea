"""
Supabase Storage Configuration
Handles image uploads to Supabase Storage buckets.
"""
from supabase import create_client, Client
import os
from typing import Optional
import base64
from io import BytesIO

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use system environment variables
    pass

class SupabaseStorage:
    """Handle Supabase Storage operations for images."""
    
    def __init__(self):
        # Get Supabase URL and Key from environment
        # Try service role key first (for uploads), fall back to anon key
        supabase_url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0")
        
        print(f"INFO: Initializing Supabase client with URL: {supabase_url}")
        key_type = 'SERVICE_ROLE' if os.getenv('SUPABASE_SERVICE_ROLE_KEY') else 'ANON'
        print(f"INFO: Using key type: {key_type}")
        
        # Store URL for fallback URL generation
        self.supabase_url = supabase_url
        
        try:
            self.client: Client = create_client(supabase_url, supabase_key)
            print("SUCCESS: Supabase client initialized")
            
            # Test if we can access storage
            try:
                # Try to list buckets to verify connection
                buckets = self.client.storage.list_buckets()
                bucket_names = [b.name for b in buckets] if buckets else []
                print(f"INFO: Successfully connected to Supabase Storage. Available buckets: {bucket_names}")
                
                # Check if our target bucket exists
                if "shop-registrations" not in bucket_names:
                    print(f"WARNING: Bucket 'shop-registrations' not found. Available buckets: {bucket_names}")
                    print(f"WARNING: Please create the bucket 'shop-registrations' in Supabase Storage")
            except Exception as test_error:
                print(f"WARNING: Could not list buckets: {type(test_error).__name__}: {str(test_error)}")
        except Exception as e:
            print(f"ERROR: Could not initialize Supabase client: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            self.client = None
    
    def upload_image(
        self, 
        bucket_name: str, 
        file_path: str, 
        file_content: bytes,
        content_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Upload image to Supabase Storage.
        
        Args:
            bucket_name: Name of the bucket (e.g., "shop-registrations")
            file_path: Path within bucket (e.g., "cnic/front/shop_123_cnic_front_20240101.jpg")
            file_content: Image file content as bytes
            content_type: MIME type (e.g., "image/jpeg", "image/png")
        
        Returns:
            Public URL of uploaded image or None if failed
        """
        if not self.client:
            print(f"ERROR: Supabase client not initialized. Cannot upload to {bucket_name}/{file_path}")
            return None
        
        # Check if bucket exists (non-blocking - just for info)
        # Note: ANON key may not have permission to list buckets, so we'll try upload anyway
        try:
            buckets = self.client.storage.list_buckets()
            bucket_names = [b.name for b in buckets] if buckets else []
            if bucket_name not in bucket_names:
                print(f"WARNING: Bucket '{bucket_name}' not found in list. Available buckets: {bucket_names}")
                print(f"WARNING: This might be a permissions issue. Will attempt upload anyway...")
            else:
                print(f"INFO: Bucket '{bucket_name}' verified to exist")
        except Exception as bucket_check_error:
            print(f"WARNING: Could not verify bucket existence (may be permissions issue): {type(bucket_check_error).__name__}: {str(bucket_check_error)}")
            print(f"WARNING: Will attempt upload anyway - upload will fail with clear error if bucket doesn't exist")
            # Continue anyway - let the upload fail if bucket doesn't exist
            
        try:
            print(f"INFO: Attempting to upload {len(file_content)} bytes to {bucket_name}/{file_path}")
            
            # Track Supabase call timing
            import time
            supabase_start = time.time()
            
            # Supabase Python client upload method
            # The upload method signature: upload(path, file, file_options=None)
            # file_options should only contain "content-type" as a string
            # Note: upsert is not supported in file_options for Python client
            try:
                # Upload with file_options (content-type only)
                response = self.client.storage.from_(bucket_name).upload(
                    path=file_path,
                    file=file_content,
                    file_options={
                        "content-type": content_type
                    }
                )
                
                # Track upload time
                supabase_upload_time = (time.time() - supabase_start) * 1000
                
                print(f"INFO: Upload response type: {type(response)}")
                print(f"INFO: Upload response: {response}")
                
                # Check if response has error attribute
                if hasattr(response, 'error') and response.error:
                    print(f"ERROR: Upload failed with error: {response.error}")
                    return None
                
                # Check if response is a dict with error
                if isinstance(response, dict):
                    if response.get('error'):
                        error_msg = response.get('error', {}).get('message', 'Unknown error')
                        print(f"ERROR: Upload failed with error: {error_msg}")
                        return None
                    # If successful, response might have 'path' key
                    uploaded_path = response.get('path', file_path)
                elif hasattr(response, 'path'):
                    # Response object with path attribute
                    uploaded_path = response.path
                else:
                    # Assume success and use original path
                    uploaded_path = file_path
                
                # Get public URL (track timing)
                url_start = time.time()
                url_response = self.client.storage.from_(bucket_name).get_public_url(uploaded_path)
                supabase_url_time = (time.time() - url_start) * 1000
                supabase_total_time = supabase_upload_time + supabase_url_time
                
                # Handle different response types from get_public_url
                if isinstance(url_response, dict):
                    url = url_response.get('publicUrl') or url_response.get('public_url')
                elif hasattr(url_response, 'publicUrl'):
                    url = url_response.publicUrl
                elif hasattr(url_response, 'public_url'):
                    url = url_response.public_url
                else:
                    url = str(url_response) if url_response else None
                
                if url:
                    print(f"INFO: Generated public URL: {url} (Supabase time: {supabase_total_time:.2f}ms)")
                    # Store Supabase timing in thread-local storage for middleware to pick up
                    try:
                        import threading
                        if not hasattr(threading.current_thread(), 'supabase_calls'):
                            threading.current_thread().supabase_calls = []
                        threading.current_thread().supabase_calls.append({
                            "operation": f"upload_image:{bucket_name}",
                            "time_ms": supabase_total_time
                        })
                    except:
                        pass  # Ignore if tracking fails
                    return url
                else:
                    print(f"ERROR: Could not get public URL. Response: {url_response}")
                    # Fallback: construct URL manually
                    base_url = self.supabase_url.rstrip('/')
                    url = f"{base_url}/storage/v1/object/public/{bucket_name}/{uploaded_path}"
                    print(f"INFO: Using fallback URL: {url}")
                    return url
                    
            except Exception as upload_error:
                print(f"ERROR in upload call: {type(upload_error).__name__}: {str(upload_error)}")
                import traceback
                traceback.print_exc()
                
                # Try alternative method signature (positional args with file_options)
                try:
                    print(f"INFO: Trying alternative upload method (positional args, content-type only)...")
                    alt_start = time.time()
                    response = self.client.storage.from_(bucket_name).upload(
                        file_path,
                        file_content,
                        file_options={
                            "content-type": content_type
                        }
                    )
                    alt_upload_time = (time.time() - alt_start) * 1000
                    
                    print(f"INFO: Alternative upload response: {response}")
                    
                    # Handle response same way
                    if hasattr(response, 'error') and response.error:
                        print(f"ERROR: Alternative method failed: {response.error}")
                        return None
                    
                    if isinstance(response, dict) and response.get('error'):
                        print(f"ERROR: Alternative method failed: {response.get('error')}")
                        return None
                    
                    # Get URL (track timing)
                    url_start = time.time()
                    url_response = self.client.storage.from_(bucket_name).get_public_url(file_path)
                    alt_url_time = (time.time() - url_start) * 1000
                    alt_total_time = alt_upload_time + alt_url_time
                    
                    if isinstance(url_response, dict):
                        url = url_response.get('publicUrl') or url_response.get('public_url')
                    elif hasattr(url_response, 'publicUrl'):
                        url = url_response.publicUrl
                    else:
                        url = str(url_response) if url_response else None
                    
                    if url:
                        print(f"INFO: Alternative method succeeded. URL: {url} (Supabase time: {alt_total_time:.2f}ms)")
                        # Store Supabase timing in thread-local storage
                        try:
                            import threading
                            if not hasattr(threading.current_thread(), 'supabase_calls'):
                                threading.current_thread().supabase_calls = []
                            threading.current_thread().supabase_calls.append({
                                "operation": f"upload_image:{bucket_name}",
                                "time_ms": alt_total_time
                            })
                        except:
                            pass
                        return url
                    else:
                        # Fallback URL
                        base_url = self.supabase_url.rstrip('/')
                        url = f"{base_url}/storage/v1/object/public/{bucket_name}/{file_path}"
                        print(f"INFO: Using fallback URL: {url}")
                        return url
                        
                except Exception as alt_error:
                    print(f"ERROR: Alternative method also failed: {type(alt_error).__name__}: {str(alt_error)}")
                    import traceback
                    traceback.print_exc()
                    return None
        except Exception as e:
            print(f"ERROR uploading image to {bucket_name}/{file_path}: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def upload_base64_image(
        self,
        bucket_name: str,
        file_path: str,
        base64_string: str,
        content_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Upload base64 encoded image to Supabase Storage.
        
        Args:
            bucket_name: Name of the bucket
            file_path: Path within bucket
            base64_string: Base64 encoded image (with or without data URI prefix)
            content_type: MIME type
        
        Returns:
            Public URL of uploaded image or None if failed
        """
        try:
            if not self.client:
                print(f"ERROR: Supabase client not initialized. Cannot upload to {bucket_name}/{file_path}")
                return None
            
            if not base64_string or base64_string.strip() == "":
                print(f"ERROR: Empty base64 string provided for {bucket_name}/{file_path}")
                return None
            
            # Remove data URI prefix if present
            if base64_string.startswith("data:"):
                base64_string = base64_string.split(",")[1]
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_string)
            print(f"INFO: Decoded {len(image_bytes)} bytes from base64 for {bucket_name}/{file_path}")
            
            url = self.upload_image(bucket_name, file_path, image_bytes, content_type)
            if url:
                print(f"SUCCESS: Uploaded image to {url}")
            else:
                print(f"ERROR: Upload failed for {bucket_name}/{file_path}")
            return url
        except Exception as e:
            print(f"ERROR uploading base64 image to {bucket_name}/{file_path}: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def delete_image(self, bucket_name: str, file_path: str) -> bool:
        """Delete image from Supabase Storage."""
        if not self.client:
            return False
            
        try:
            self.client.storage.from_(bucket_name).remove([file_path])
            return True
        except Exception as e:
            print(f"Error deleting image: {e}")
            return False
    
    def get_image_url(self, bucket_name: str, file_path: str) -> str:
        """Get public URL for an image."""
        if not self.client:
            return ""
        return self.client.storage.from_(bucket_name).get_public_url(file_path)

# Global instance
storage = SupabaseStorage()

