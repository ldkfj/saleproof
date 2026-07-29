import React, { useState } from "react";
import { BOND_ADDRESS } from "../lib/chain";
import { buildAddProductRequest } from "../lib/product";
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
  const invalidUrl = (() => {
    try {
      buildAddProductRequest(BOND_ADDRESS as `0x${string}`, productUrl);
      return false;
    } catch {
      return true;
    }
  })();

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
          request={() =>
            buildAddProductRequest(
              BOND_ADDRESS as `0x${string}`,
              productUrl,
            )
          }
          onSuccess={onSuccess}
          disabled={!merchantActive || invalidUrl}
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
