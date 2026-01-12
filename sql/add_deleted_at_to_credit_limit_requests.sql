-- Add deleted_at column to credit_limit_requests table for soft delete functionality
-- This allows credit limit requests to be soft deleted when their associated shop is deleted

ALTER TABLE public.credit_limit_requests 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.credit_limit_requests.deleted_at IS 
'Soft delete timestamp. When set, request is considered deleted but data is preserved for audit. NULL = active record.';

-- Create index for better query performance when filtering by deleted_at
CREATE INDEX IF NOT EXISTS idx_credit_limit_requests_deleted_at 
ON public.credit_limit_requests(deleted_at) 
WHERE deleted_at IS NULL;


