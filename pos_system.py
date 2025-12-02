# pos_system.py
import pandas as pd
import database
import uuid

class POSSystem:
    def __init__(self):
        self.currency_symbol = database.CURRENCY
        self.pending_orders = []

    def get_available_menu(self):
        """Checks menu against inventory to determine availability."""
        df_menu = database.load_sheet(database.SHEET_MENU)
        df_inventory = database.load_sheet(database.SHEET_INVENTORY)
        
        available_menu = []
        
        # Get unique menu items and their pricing details
        unique_menus = df_menu.drop_duplicates(subset=['Menu Item Name', 'Size/Container'])
        
        for index, menu_row in unique_menus.iterrows():
            menu_name = menu_row['Menu Item Name']
            size = menu_row['Size/Container']
            is_available = True
            
            # Filter all ingredient rows for the current menu item/size
            item_ingredients = df_menu[
                (df_menu['Menu Item Name'] == menu_name) & 
                (df_menu['Size/Container'] == size)
            ]
            missing_ingredient = None
            
            # Check stock for each ingredient required
            for _, ing_row in item_ingredients.iterrows():
                ing_name = ing_row['Ingredient Name']
                qty_needed = ing_row['Needed Quantity (g/ml)']
                
                inv_match = df_inventory[df_inventory['Ingredient Name'] == ing_name]
                
                if inv_match.empty:
                    # Ingredient doesn't exist in inventory
                    is_available = False
                    missing_ingredient = ing_name
                    break
                
                current_stock = inv_match['Current Stock (g/ml)'].iloc[0]
                
                if current_stock < qty_needed:
                    is_available = False
                    missing_ingredient = ing_name
                    break
            
            # Append menu item with availability status
            menu_data = {
                'Menu Item Name': menu_name,
                'Size/Container': size,
                'Selling Price': menu_row['Suggested Selling Price (₱)'],
                'Available': is_available,
                'MissingIngredient': missing_ingredient
            }
            available_menu.append(menu_data)

        return available_menu

    def place_order(self, available_menu):
        """Prompts for order details."""
        print("## 📝 Place New Order 📝")
        name_or_table = input("Enter Customer Name or Table Number: ").strip()
        
        order_items = []
        order_id = str(uuid.uuid4())
        
        while True:
            print("\n--- Available Menu ---")
            for i, item in enumerate(available_menu):
                if item['Available']:
                    status = "✅"
                    print(f"  {i+1}. {item['Menu Item Name']} ({item['Size/Container']}) - {self.currency_symbol}{item['Selling Price']:.2f} {status}")
                else:
                    print(f"  {i+1}. {item['Menu Item Name']} ({item['Size/Container']}) - {self.currency_symbol}{item['Selling Price']:.2f} ❌ (LOW STOCK: {item['MissingIngredient']})")
            
            choice = input("\nEnter item number to add (or type **'done'**): ").strip()
            if choice.lower() == 'done':
                break
            
            try:
                index = int(choice) - 1
                if 0 <= index < len(available_menu):
                    selected_item = available_menu[index]
                    
                    if not selected_item['Available']:
                        print("🚫 Cannot order: Item is currently low on stock.")
                        continue

                    order_items.append({
                        'OrderID': order_id,
                        'Customer/Table': name_or_table,
                        'Menu Item Name': selected_item['Menu Item Name'],
                        'Size/Container': selected_item['Size/Container'],
                        'Price': selected_item['Selling Price'],
                        'Status': 'PENDING'
                    })
                    print(f"Added {selected_item['Menu Item Name']} to order.")
                else:
                    print("Invalid menu number.")
            except ValueError:
                print("Invalid input.")

        if order_items:
            self.pending_orders.extend(order_items)
            print(f"\nOrder for {name_or_table} placed with {len(order_items)} items.")

    def view_pending_orders(self):
        """Displays currently pending orders."""
        print("\n## 🔔 Pending Orders 🔔")
        if not self.pending_orders:
            print("No pending orders.")
            return

        df_pending = pd.DataFrame(self.pending_orders)
        
        # Group by OrderID to show orders neatly
        for order_id, group in df_pending.groupby('OrderID'):
            table = group['Customer/Table'].iloc[0]
            total = group['Price'].sum()
            print(f"\nOrder ID: {order_id} | Customer/Table: {table} | Total: {self.currency_symbol}{total:.2f}")
            for _, item in group.iterrows():
                print(f"  - {item['Menu Item Name']} ({item['Size/Container']}) [Status: {item['Status']}]")

    def serve_order(self):
        """Marks an order as served and deducts inventory."""
        print("\n## ✅ Mark Order as Served ✅")
        if not self.pending_orders:
            print("No pending orders to serve.")
            return
            
        df_pending = pd.DataFrame(self.pending_orders)
        unique_orders = df_pending.drop_duplicates(subset=['OrderID'])

        print("--- Orders to Serve ---")
        for i, (order_id, row) in enumerate(unique_orders.iterrows()):
            print(f"{i+1}. Order ID: {row['OrderID'][:8]}... | Table: {row['Customer/Table']}")
        
        choice = input("Enter the number of the order to **SERVE** (or 'cancel'): ").strip()
        if choice.lower() == 'cancel':
            return

        try:
            index = int(choice) - 1
            selected_id = unique_orders.iloc[index]['OrderID']
            
            # --- Deduction Logic ---
            df_menu = database.load_sheet(database.SHEET_MENU)
            
            items_served = [item for item in self.pending_orders if item['OrderID'] == selected_id and item['Status'] == 'PENDING']
            
            for item in items_served:
                item['Status'] = 'SERVED' # Update status in memory
                
                # Get the required ingredients for the item
                item_ingredients = df_menu[
                    (df_menu['Menu Item Name'] == item['Menu Item Name']) & 
                    (df_menu['Size/Container'] == item['Size/Container'])
                ]
                
                # Deduct stock for each ingredient
                for _, ing_row in item_ingredients.iterrows():
                    ing_name = ing_row['Ingredient Name']
                    qty_needed = ing_row['Needed Quantity (g/ml)']
                    database.update_inventory(ing_name, qty_needed)
                    
            print(f"✅ Order {selected_id[:8]}... marked as **SERVED** and inventory deducted.")
            
            # --- Cash Flow Accounting ---
            self.account_cash_flow(selected_id)

            # Remove served items from pending list
            self.pending_orders = [item for item in self.pending_orders if item['Status'] == 'PENDING']
            
        except (ValueError, IndexError):
            print("Invalid order number.")

    def account_cash_flow(self, order_id):
        """Records the served order for daily sales/cash flow."""
        df_pending = pd.DataFrame(self.pending_orders)
        served_order = df_pending[df_pending['OrderID'] == order_id] # Assuming we check based on the initial ID
        
        if served_order.empty: return

        # Load existing sales/cash flow data (assuming this is a separate sheet or aggregated later)
        # For simplicity, we'll append to a 'Daily_Sales' sheet
        df_sales = database.load_sheet(database.SHEET_SALES)
        
        total_sale = served_order['Price'].sum()
        
        sales_data = {
            'SaleID': order_id,
            'Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Total Sale (₱)': total_sale,
            'Customer/Table': served_order['Customer/Table'].iloc[0],
            'Items Count': len(served_order)
        }
        
        df_new_sale = pd.DataFrame([sales_data])
        
        if not df_sales.empty:
            df_sales_combined = pd.concat([df_sales, df_new_sale], ignore_index=True)
        else:
            df_sales_combined = df_new_sale
            
        database.save_dataframe(df_sales_combined, database.SHEET_SALES)
        print(f"💰 Cash Flow recorded: Sale of {self.currency_symbol}{total_sale:.2f}.")

    def run(self):
        while True:
            menu = self.get_available_menu()
            print("\n" + "="*50)
            print("    COFFEE SHOP POINT OF SALE (POS) SYSTEM    ")
            print("="*50)
            print("1. Place New Order")
            print("2. View Pending Orders (for Kitchen)")
            print("3. Mark Order as Served (Deducts Stock)")
            print("4. Exit POS")
            
            choice = input("Enter choice (1-4): ").strip()

            if choice == '1':
                self.place_order(menu)
            elif choice == '2':
                self.view_pending_orders()
            elif choice == '3':
                self.serve_order()
            elif choice == '4':
                print("Exiting POS System.")
                break
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    app = POSSystem()
    app.run()