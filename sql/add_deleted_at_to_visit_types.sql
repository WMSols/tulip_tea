-- Add deleted_at column to visit_types table for soft delete functionality
-- This allows visit type associations to be soft deleted without removing data

ALTER TABLE public.visit_types 
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITHOUT TIME ZONE NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.visit_types.deleted_at IS 
'Soft delete timestamp. When set, visit type association is considered deleted but data is preserved. NULL = active record.';

-- Create index for better query performance when filtering by deleted_at
CREATE INDEX IF NOT EXISTS idx_visit_types_deleted_at 
ON public.visit_types(deleted_at) 
WHERE deleted_at IS NULL;

