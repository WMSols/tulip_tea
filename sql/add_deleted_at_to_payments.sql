-- Add deleted_at column to payments table for soft delete functionality
-- This allows payments to be soft deleted without removing financial audit data

ALTER TABLE public.payments 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.payments.deleted_at IS 
'Soft delete timestamp. When set, payment is considered deleted but data is preserved for financial audit. NULL = active record.';

-- Create index for better query performance when filtering by deleted_at
CREATE INDEX IF NOT EXISTS idx_payments_deleted_at 
ON public.payments(deleted_at) 
WHERE deleted_at IS NULL;

