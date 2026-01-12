-- Add outstanding_balance column to shops table
-- This tracks the current outstanding dues (unpaid orders - payments + legacy_balance)

ALTER TABLE public.shops 
ADD COLUMN IF NOT EXISTS outstanding_balance NUMERIC(10, 2) DEFAULT 0 NOT NULL;

-- Add comment to document the column
COMMENT ON COLUMN public.shops.outstanding_balance IS 
'Current outstanding balance (dues) for the shop. Calculated as: (Total unpaid orders) - (Total payments) + (Legacy balance). Updated automatically when orders are created or payments are received.';

-- Update existing shops to calculate their outstanding balance
-- Note: This is a one-time calculation. After this, it will be maintained automatically.
UPDATE public.shops s
SET outstanding_balance = COALESCE((
    SELECT COALESCE(SUM(o.total_amount), 0)
    FROM orders o
    WHERE o.shop_id = s.id
    AND o.status NOT IN ('paid', 'cancelled')
    AND o.deleted_at IS NULL
), 0) - COALESCE((
    SELECT COALESCE(SUM(p.amount), 0)
    FROM payments p
    WHERE p.shop_id = s.id
    AND p.deleted_at IS NULL
), 0) + COALESCE(s.legacy_balance, 0)
WHERE s.deleted_at IS NULL;

