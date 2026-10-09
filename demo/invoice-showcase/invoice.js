// discountPercent is a percentage: 10 means a ten percent discount.
export function invoiceTotal(price, discountPercent) {
  return price - discountPercent;
}
