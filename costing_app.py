# costing_app.py
import pandas as pd
import database
import uuid # For generating unique IDs

class CostingApp:
    def __init__(self):
        self.currency_symbol = database.CURRENCY

    def get_profit_percent(self):
        """Prompts the user for the desired profit percentage."""
        while True:
            try:
                profit_margin = float(input("Enter the desired **Profit Percentage** (e.g., 50 for 50%): "))
                if profit_margin > 0:
                    return profit_margin
                else:
                    print("Profit percentage must be greater than zero.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def get_ingredient_data(self, drink_name):
        """Collects ingredient details for a single drink."""
        print(f"\n--- Ingredients for {drink_name} ---")
        ingredients = []
        current_ingredient_cost_total = 0.0

        while True:
            ingredient_name = input("Enter ingredient name (or type **'done'** to finish): ").strip()
            if ingredient_name.lower() == 'done':
                break
            if not ingredient_name:
                continue
            
            # --- Check Inventory for Unit Cost ---
            df_inventory = database.load_sheet(database.SHEET_INVENTORY)
            inv_match = df_inventory[df_inventory['Ingredient Name'].str.lower() == ingredient_name.lower()]
            
            cost_per_unit = 0
            unit = 'g' # Default
            
            if not inv_match.empty:
                cost_per_unit = inv_match['Cost/Unit'].iloc[0]
                unit = inv_match['Unit (g/ml)'].iloc[0]
                print(f"  Found '{ingredient_name}' in Inventory. Cost/Unit: {self.currency_symbol}{cost_per_unit:.4f} / {unit}")
            else:
                print(f"  Warning: '{ingredient_name}' not found in Inventory. Please add it via Inventory Restock.")
                continue # Skip ingredient if not in inventory to enforce cost tracking

            while True:
                try:
                    needed_quantity = float(input(f"  Quantity of **{ingredient_name}** needed for the drink ({unit}): "))
                    break
                except ValueError:
                    print("  Invalid input. Please enter a valid quantity.")
            
            ingredient_cost = cost_per_unit * needed_quantity
            current_ingredient_cost_total += ingredient_cost

            print("-" * 25)
            print(f"**Ingredient Cost for {ingredient_name}:** {self.currency_symbol}{ingredient_cost:.2f}")
            print(f"**RUNNING INGREDIENT TOTAL:** {self.currency_symbol}{current_ingredient_cost_total:.2f}")
            print("-" * 25)

            ingredients.append({
                'MenuID': str(uuid.uuid4()), # Unique ID for each ingredient row
                'Ingredient Name': ingredient_name,
                'Unit (g/ml)': unit,
                'Cost/Unit (₱)': cost_per_unit,
                'Needed Quantity (g/ml)': needed_quantity,
                'Ingredient Cost (₱)': ingredient_cost
            })
        return ingredients, current_ingredient_cost_total

    def run(self):
        """Main function to create and append menu items."""
        print("## 💰 Menu Costing and Pricing 💰")
        profit_percent = self.get_profit_percent()
        menu_rows = []

        while True:
            print("\n" + "=" * 40)
            menu_name = input("Enter the **Menu Item Name** (e.g., Iced Latte / Clubhouse Sandwich) or type **'quit'** to save and exit: ").strip()
            
            if menu_name.lower() == 'quit':
                break
            if not menu_name:
                continue

            cup_size = input("Enter **Size/Container** (e.g., 16oz, Small, 1pc): ").strip()

            ingredients, total_ingredient_cost = self.get_ingredient_data(menu_name)
            
            if not ingredients:
                print("No ingredients added. Skipping menu item.")
                continue

            while True:
                try:
                    other_costs = float(input(f"\nEnter **Other Variable Costs** (Cup/Plate, Lid, Straw, Sticker, Labor, {self.currency_symbol}5.00): {self.currency_symbol}"))
                    break
                except ValueError:
                    print("Invalid input. Please enter a valid cost.")
            
            total_prime_cost = total_ingredient_cost + other_costs
            suggested_price = total_prime_cost / (1 - (profit_percent / 100))
            profit_amount = suggested_price - total_prime_cost

            print("\n--- **Calculated Results** ---")
            print(f"**Total Ingredient Cost:** {self.currency_symbol}{total_ingredient_cost:.2f}")
            print(f"**Total Prime Cost (Ingredients + Other Costs):** {self.currency_symbol}{total_prime_cost:.2f}")
            print(f"**Target Profit ({profit_percent:.1f}%):** {self.currency_symbol}{profit_amount:.2f}")
            print(f"**Suggested Selling Price:** **{self.currency_symbol}{suggested_price:.2f}**")
            print("-" * 28)

            # Store the data for saving to Excel
            for ingredient in ingredients:
                row = {
                    'Menu Item Name': menu_name,
                    'Size/Container': cup_size,
                    'Profit Target (%)': profit_percent,
                    'Other Variable Costs (₱)': other_costs,
                    'Total Prime Cost (₱)': total_prime_cost,
                    'Suggested Selling Price (₱)': suggested_price,
                    'Profit Amount (₱)': profit_amount,
                    'Ingredient Name': ingredient['Ingredient Name'],
                    'Unit (g/ml)': ingredient['Unit (g/ml)'],
                    'Cost/Unit (₱)': ingredient['Cost/Unit (₱)'],
                    'Needed Quantity (g/ml)': ingredient['Needed Quantity (g/ml)'],
                    'Ingredient Cost (₱)': ingredient['Ingredient Cost (₱)'],
                    'MenuIngredientID': ingredient['MenuID'] # Link to POS for deduction
                }
                menu_rows.append(row)
            
            # Add blank row for readability in the sheet
            menu_rows.append({}) 

        # Load existing data and append new menu rows
        df_existing = database.load_sheet(database.SHEET_MENU)
        df_new = pd.DataFrame(menu_rows)
        
        if not df_existing.empty:
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        database.save_dataframe(df_combined, database.SHEET_MENU)
        print("\n✅ Menu costing data saved to the database.")

if __name__ == "__main__":
    app = CostingApp()
    app.run()