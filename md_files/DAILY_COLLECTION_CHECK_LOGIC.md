# Daily Collection Check Logic (Payment Before Delivery)

## When is "daily collection" considered done for an order?

The system treats payment as **collected for an order** when the order’s **`payment_collected_before_delivery`** flag is `true`.

### How the flag gets set (backend)

1. **POST /orders/{order_id}/collect-payment**  
   Delivery man collects payment at shop → backend sets:
   - `order.payment_collected_before_delivery = true`
   - `order.payment_collected_amount`, `order.payment_collected_at`
   - Reduces shop outstanding balance.

2. **POST /daily-collections/delivery-man/{id}** (with `order_id` in body)  
   - Currently: creates a daily collection, reduces shop outstanding, does **not** set `order.payment_collected_before_delivery`.  
   - To treat “daily collection” as satisfying payment-before-delivery: backend should, when `order_id` is present and that order has `order_resolution_type === 'payment_before_delivery'`, set `payment_collected_before_delivery` (and amount/at) on that order.

### Frontend (delivery man dashboard)

- **Orders list** comes from **GET /orders/delivery-man/{id}?pending=true**. Each order includes:
  - `order_resolution_type` (e.g. `'payment_before_delivery'`)
  - `payment_collected_before_delivery` (boolean)
  - `payment_collected_amount`, `payment_collected_at` (optional)

- **Check used for “can deliver”**
  - `requiresPaymentBeforeDelivery` = `(order.order_resolution_type || '').toLowerCase() === 'payment_before_delivery'`
  - `paymentBeforeDeliverySatisfied` = `!!order.payment_collected_before_delivery`
  - **`canDeliver`** = `!requiresPaymentBeforeDelivery || paymentBeforeDeliverySatisfied`

- **UI behaviour**
  - If **`canDeliver`** is false and status is `picked_up` or `in_transit`: show message “Complete daily collection for this order before delivering” and only the **Daily Collection** button (no “Deliver to Shop”).
  - If **`canDeliver`** is false and status is `partially_delivered`: same message, show **Daily Collection** and **Return Remaining Stock**, but no “Update Delivery” until collection is done.
  - When submitting **Daily Collection**, frontend sends **`order_id`** so the backend can link the collection to the order (and, if implemented, set `payment_collected_before_delivery`).

- **Deliver API error**
  - If **POST /deliveries/{id}/deliver** returns 400 and the message mentions payment/collection, the frontend shows: “Payment must be collected before delivery. Complete daily collection for this order first, then try again.”

## Summary

| Concept | Meaning |
|--------|--------|
| **Order requires payment before delivery** | `order.order_resolution_type === 'payment_before_delivery'` |
| **Payment considered “done” for that order** | `order.payment_collected_before_delivery === true` |
| **Daily collection “counts” for the order** | When backend sets `payment_collected_before_delivery` on the order (e.g. when daily collection is submitted with that `order_id`). |
| **Frontend “can deliver”** | Either order is not payment_before_delivery, or payment_collected_before_delivery is true. |
