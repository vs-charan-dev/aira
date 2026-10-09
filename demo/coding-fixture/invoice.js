// Demo defect: the discount argument is a percentage, e.g. 10 means ten percent.
export function invoiceTotal(price, discountPercent) {
  return price - discountPercent;
}
