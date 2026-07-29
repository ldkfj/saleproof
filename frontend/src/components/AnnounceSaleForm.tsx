import React, { useEffect, useState } from "react";
import type { Product } from "../lib/contracts";
import { BOND_ADDRESS } from "../lib/chain";
import {
  buildAnnounceSaleArgs,
  SALE_CURRENCIES,
  type SaleCurrency,
} from "../lib/sale";
import { TxAction } from "./TxAction";

interface AnnounceSaleFormProps {
  products: Product[];
  merchantActive: boolean;
  saleCount: number;
  onSuccess: () => Promise<void> | void;
}

export const AnnounceSaleForm: React.FC<AnnounceSaleFormProps> = ({
  products,
  merchantActive,
  saleCount,
  onSuccess,
}) => {
  const [selectedProductId, setSelectedProductId] = useState(() =>
    products[0] ? String(products[0].id) : "",
  );
  const [referencePrice, setReferencePrice] = useState("65.00");
  const [discountPercent, setDiscountPercent] = useState("20");
  const [duration, setDuration] = useState("86400");
  const [currency, setCurrency] = useState<SaleCurrency>("GBP");

  useEffect(() => {
    if (
      !products.some((product) => String(product.id) === selectedProductId)
    ) {
      setSelectedProductId(products[0] ? String(products[0].id) : "");
    }
  }, [products, selectedProductId]);

  const buildRequest = () => ({
    address: BOND_ADDRESS as `0x${string}`,
    functionName: "announce_sale",
    args: buildAnnounceSaleArgs({
      productId: Number(selectedProductId),
      referencePrice,
      discountPercent,
      durationSeconds: Number(duration),
      currency,
    }),
  });

  const invalidInput = (() => {
    try {
      buildRequest();
      return false;
    } catch {
      return true;
    }
  })();

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">
            {saleCount === 0 ? "Announce Your First Sale" : "Announce Sale"}
          </h2>
          {saleCount === 0 && (
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
              Create the first sale directly from this dashboard after adding a product.
            </p>
          )}
        </div>
      </div>
      <div className="grid-3">
        <label>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Product</span>
          <select
            className="search-input"
            value={selectedProductId}
            onChange={(event) => setSelectedProductId(event.target.value)}
          >
            <option value="">Select your product</option>
            {products.map((product) => (
              <option key={product.id} value={product.id}>
                Product #{product.id}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            Reference price ({currency})
          </span>
          <input
            className="search-input"
            value={referencePrice}
            inputMode="decimal"
            onChange={(event) => setReferencePrice(event.target.value)}
          />
        </label>
        <label>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Currency</span>
          <select
            className="search-input"
            value={currency}
            onChange={(event) => setCurrency(event.target.value as SaleCurrency)}
          >
            {SALE_CURRENCIES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Discount %</span>
          <input
            className="search-input"
            value={discountPercent}
            inputMode="decimal"
            onChange={(event) => setDiscountPercent(event.target.value)}
          />
        </label>
        <label>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Duration</span>
          <select
            className="search-input"
            value={duration}
            onChange={(event) => setDuration(event.target.value)}
          >
            <option value="3600">1 hour</option>
            <option value="86400">24 hours</option>
            <option value="604800">7 days</option>
            <option value="2592000">30 days</option>
          </select>
        </label>
        <TxAction
          label="Announce Sale"
          request={buildRequest}
          onSuccess={onSuccess}
          disabled={!merchantActive || products.length === 0 || invalidInput}
          disabledReason={
            !merchantActive
              ? "Only an active registered merchant can announce sales."
              : products.length === 0
                ? "Add an active product before announcing a sale."
                : "Select a product and enter a valid price and 1-95% discount."
          }
          persistenceKey="announce-sale"
        />
      </div>
    </div>
  );
};
