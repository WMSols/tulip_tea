-- Add deleted_at column to shop_visits table for soft delete functionality
-- This allows visits to be soft deleted (marked as deleted) without removing data from the database

ALTER TABLE public.shop_visits 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.shop_visits.deleted_at IS 
'Soft delete timestamp. When set, visit is considered deleted but data is preserved for audit. NULL = active record.';

-- Create index for better query performance when filtering by deleted_at
CREATE INDEX IF NOT EXISTS idx_shop_visits_deleted_at 
ON public.shop_visits(deleted_at) 
WHERE deleted_at IS NULL;



