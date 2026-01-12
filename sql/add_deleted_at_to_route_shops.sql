-- Add deleted_at column to route_shops table for soft delete functionality
-- This allows route-shop relationships to be soft deleted without removing data

ALTER TABLE public.route_shops 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.route_shops.deleted_at IS 
'Soft delete timestamp. When set, route-shop relationship is considered deleted but data is preserved. NULL = active record.';

-- Create index for better query performance when filtering by deleted_at
CREATE INDEX IF NOT EXISTS idx_route_shops_deleted_at 
ON public.route_shops(deleted_at) 
WHERE deleted_at IS NULL;

