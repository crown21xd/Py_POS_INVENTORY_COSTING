# inventory_manager.py
import pandas as pd
import database

class InventoryManager:
    def __init__(self):
        self.currency_symbol = database.CURRENCY

    def restock(self):
        """Prompts for restock details, calculates unit cost, and updates inventory."""
        print("## 📦 Inventory Restock 📦")
        df_inventory = database.load_sheet(database.SHEET_INVENTORY)

        required_cols = [
            'Ingredient Name', 'Last Whole Sale Price (₱)', 'Bulk Quantity (g/ml)',
            'Unit (g/ml)', 'Delivery Fee (₱)', 'Total Cost (₱)',
            'Cost/Unit', 'Current Stock (g/ml)'
        ]

        if df_inventory.empty or 'Ingredient Name' not in df_inventory.columns:
            print("Creating new Inventory sheet structure...")
            df_inventory = pd.DataFrame(columns=required_cols)

        changes_made = False

        while True:
            print("\n" + "=" * 40)
            item_name = input("Enter **Ingredient Name** to restock (or type **'quit'**): ").strip()
            if item_name.lower() == 'quit':
                break
            if not item_name: continue

            # Check if item exists to get existing stock/unit
            is_new_item = item_name not in df_inventory['Ingredient Name'].values

            while True:
                try:
                    wholesale_price = float(input(f"  Whole sale **Price** of bulk item: {self.currency_symbol}"))
                    bulk_quantity = float(input("  Bulk **Quantity** (grams/ml/units): "))
                    if is_new_item:
                        unit = input("  Unit (**g**/**ml**/**pc**): ").strip().lower()
                    else:
                        # Use existing unit if item already exists
                        unit = df_inventory[df_inventory['Ingredient Name'] == item_name]['Unit (g/ml)'].iloc[0]
                        print(f"  Using existing unit: {unit}")
                    delivery_fee = float(input(f"  **Delivery Fee** for this item: {self.currency_symbol}"))
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            # Calculate total cost of the item including proportional delivery fee
            total_bulk_cost = wholesale_price + delivery_fee

            # Calculate the cost per unit (g/ml/pc)
            cost_per_unit = total_bulk_cost / bulk_quantity if bulk_quantity > 0 else 0

            # --- Handle Inventory Update ---
            if not is_new_item:
                # Update existing item
                row_index = df_inventory[df_inventory['Ingredient Name'] == item_name].index[0]

                # Update stock
                current_stock = df_inventory.loc[row_index, 'Current Stock (g/ml)']
                new_stock = current_stock + bulk_quantity
                df_inventory.loc[row_index, 'Current Stock (g/ml)'] = new_stock

                # Update cost fields (Important: Cost/Unit must be updated for costing app)
                df_inventory.loc[row_index, 'Last Whole Sale Price (₱)'] = wholesale_price
                df_inventory.loc[row_index, 'Delivery Fee (₱)'] = delivery_fee
                df_inventory.loc[row_index, 'Total Cost (₱)'] = total_bulk_cost
                df_inventory.loc[row_index, 'Cost/Unit'] = cost_per_unit

                changes_made = True
                print(f"✅ Stock updated. New total stock: {new_stock} {unit}.")
            else:
                # Add new item
                new_row = {
                    'Ingredient Name': item_name,
                    'Last Whole Sale Price (₱)': wholesale_price,
                    'Bulk Quantity (g/ml)': bulk_quantity,
                    'Unit (g/ml)': unit,
                    'Delivery Fee (₱)': delivery_fee,
                    'Total Cost (₱)': total_bulk_cost,
                    'Cost/Unit': cost_per_unit,
                    'Current Stock (g/ml)': bulk_quantity # Initial stock is the restock quantity
                }
                if df_inventory.empty:
                    df_inventory = pd.DataFrame([new_row])
                else:
                    df_inventory = pd.concat([df_inventory, pd.DataFrame([new_row])], ignore_index=True)
                changes_made = True
                print(f"✅ New ingredient added to inventory.")

        if changes_made:
            database.save_dataframe(df_inventory, database.SHEET_INVENTORY, mode='overwrite') # This will now replace the inventory file
            print("\nInventory restock complete and saved to the database.")
        else:
            print("\nNo changes made. Inventory not updated.")

    def run(self):
        self.restock()

if __name__ == "__main__":
    app = InventoryManager()
    app.run()