-- Add deleted_at column to order_items table for soft delete functionality
-- This allows order items to be soft deleted without removing order history data

ALTER TABLE public.order_items 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.order_items.deleted_at IS 
'Soft delete timestamp. When set, order item is considered deleted but data is preserved. NULL = active record.';

-- Create index for better query performance when filtering by deleted_at
CREATE INDEX IF NOT EXISTS idx_order_items_deleted_at 
ON public.order_items(deleted_at) 
WHERE deleted_at IS NULL;

