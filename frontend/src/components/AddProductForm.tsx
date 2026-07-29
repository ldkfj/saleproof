import React, { useState } from "react";
import { BOND_ADDRESS } from "../lib/chain";
import { TxAction } from "./TxAction";

interface AddProductFormProps {
  merchantActive: boolean;
  onSuccess: () => Promise<void> | void;
}

export const AddProductForm: React.FC<AddProductFormProps> = ({
  merchantActive,
  onSuccess,
}) => {
  const [productUrl, setProductUrl] = useState("");
  const url = productUrl.trim();
  const urlValid =
    url.length > 0 &&
    url.length <= 500 &&
    (url.startsWith("http://") || url.startsWith("https://"));

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Add Product</h2>
      </div>
      <div className="grid-2">
        <label>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Product URL</span>
          <input
            className="search-input"
            value={productUrl}
            maxLength={500}
            onChange={(event) => setProductUrl(event.target.value)}
            placeholder="https://merchant.example/product"
          />
        </label>
        <TxAction
          label="Add Product"
          request={() => ({
            address: BOND_ADDRESS as `0x${string}`,
            functionName: "add_product",
            args: [url],
          })}
          onSuccess={onSuccess}
          disabled={!merchantActive || !urlValid}
          disabledReason={
            !merchantActive
              ? "Only an active registered merchant can add products."
              : "Enter a valid http:// or https:// product URL."
          }
          persistenceKey="add-product"
        />
      </div>
    </div>
  );
};
