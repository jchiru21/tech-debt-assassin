import pytest
from messy_inventory import process_items, find_item, format_receipt


class TestProcessItems:
    """Test cases for process_items function"""
    
    def test_process_items_basic(self) -> None:
        """Test basic calculation with in-stock items"""
        items = [
            {"name": "item1", "price": 10.0, "quantity": 2, "in_stock": True},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": True}
        ]
        assert process_items(items) == 35.0
    
    def test_process_items_out_of_stock_excluded(self):
        """Test that out-of-stock items are excluded from total"""
        items = [
            {"name": "item1", "price": 10.0, "quantity": 2, "in_stock": True},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": False}
        ]
        assert process_items(items) == 20.0
    
    def test_process_items_missing_in_stock_key(self) -> None:
        """Test items without in_stock key (defaults to False)"""
        items = [
            {"name": "item1", "price": 10.0, "quantity": 2},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": True}
        ]
        assert process_items(items) == 15.0
    
    def test_process_items_empty_list(self) -> None:
        """Test with empty items list"""
        assert process_items([]) == 0.0
    
    def test_process_items_all_out_of_stock(self) -> None:
        """Test when all items are out of stock"""
        items = [
            {"name": "item1", "price": 10.0, "quantity": 2, "in_stock": False},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": False}
        ]
        assert process_items(items) == 0.0
    
    def test_process_items_zero_quantity(self) -> None:
        """Test items with zero quantity"""
        items = [
            {"name": "item1", "price": 10.0, "quantity": 0, "in_stock": True},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": True}
        ]
        assert process_items(items) == 15.0
    
    def test_process_items_zero_price(self) -> None:
        """Test items with zero price"""
        items = [
            {"name": "item1", "price": 0.0, "quantity": 2, "in_stock": True},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": True}
        ]
        assert process_items(items) == 15.0
    
    def test_process_items_float_values(self) -> None:
        """Test with decimal price and quantity values"""
        items = [
            {"name": "item1", "price": 10.99, "quantity": 2, "in_stock": True},
            {"name": "item2", "price": 5.50, "quantity": 1, "in_stock": True}
        ]
        assert process_items(items) == pytest.approx(27.48)
    
    def test_process_items_negative_price(self) -> None:
        """Test with negative price (edge case - refund scenario)"""
        items = [
            {"name": "item1", "price": -10.0, "quantity": 1, "in_stock": True},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": True}
        ]
        assert process_items(items) == 5.0
    
    def test_process_items_large_numbers(self) -> None:
        """Test with large price and quantity values"""
        items = [
            {"name": "item1", "price": 999999.99, "quantity": 100, "in_stock": True}
        ]
        assert process_items(items) == pytest.approx(99999999.0)
    
    def test_process_items_missing_price_key(self) -> None:
        """Test that KeyError is raised when price is missing"""
        items = [
            {"name": "item1", "quantity": 2, "in_stock": True}
        ]
        with pytest.raises(KeyError):
            process_items(items)
    
    def test_process_items_missing_quantity_key(self) -> None:
        """Test that KeyError is raised when quantity is missing"""
        items = [
            {"name": "item1", "price": 10.0, "in_stock": True}
        ]
        with pytest.raises(KeyError):
            process_items(items)
    
    def test_process_items_in_stock_false_string(self) -> None:
        """Test with in_stock as False (boolean)"""
        items = [
            {"name": "item1", "price": 10.0, "quantity": 2, "in_stock": False}
        ]
        assert process_items(items) == 0.0
    
    def test_process_items_in_stock_truthy_values(self) -> None:
        """Test with various truthy values for in_stock"""
        items = [
            {"name": "item1", "price": 10.0, "quantity": 2, "in_stock": 1},
            {"name": "item2", "price": 5.0, "quantity": 3, "in_stock": "yes"}
        ]
        assert process_items(items) == 35.0


class TestFindItem:
    """Test cases for find_item function"""
    
    def test_find_item_exists(self) -> None:
        """Test finding an existing item"""
        items = [
            {"name": "apple", "price": 1.0},
            {"name": "banana", "price": 2.0}
        ]
        result = find_item(items, "apple")
        assert result == {"name": "apple", "price": 1.0}
    
    def test_find_item_not_exists(self) -> None:
        """Test finding a non-existing item"""
        items = [
            {"name": "apple", "price": 1.0},
            {"name": "banana", "price": 2.0}
        ]
        result = find_item(items, "orange")
        assert result is None
    
    def test_find_item_empty_list(self):
        """Test finding in empty list"""
        assert find_item([], "apple") is None
    
    def test_find_item_first_match(self) -> None:
        """Test that first matching item is returned"""
        items = [
            {"name": "apple", "price": 1.0},
            {"name": "apple", "price": 2.0}
        ]
        result = find_item(items, "apple")
        assert result == {"name": "apple", "price": 1.0}
    
    def test_find_item_case_sensitive(self) -> None:
        """Test that search is case-sensitive"""
        items = [
            {"name": "apple", "price": 1.0},
            {"name": "Apple", "price": 2.0}
        ]
        result = find_item(items, "Apple")
        assert result == {"name": "Apple", "price": 2.0}
    
    def test_find_item_empty_name(self):
        """Test finding item with empty name"""
        items = [
            {"name": "", "price": 1.0},
            {"name": "apple", "price": 2.0}
        ]
        result = find_item(items, "")
        assert result == {"name": "", "price": 1.0}
    
    def test_find_item_special_characters(self):
        """Test finding item with special characters in name"""
        items = [
            {"name": "apple-pie", "price": 5.0},
            {"name": "banana_bread", "price": 4.0},
            {"name": "cherry!tart", "price": 6.0}
        ]
        result = find_item(items, "apple-pie")
        assert result == {"name": "apple-pie", "price": 5.0}
    
    def test_find_item_missing_name_key(self) -> None:
        """Test that KeyError is raised when name key is missing"""
        items = [
            {"price": 1.0}
        ]
        with pytest.raises(KeyError):
            find_item(items, "apple")
    
    def test_find_item_whitespace_name(self) -> None:
        """Test finding item with whitespace in name"""
        items = [
            {"name": "apple pie", "price": 5.0},
            {"name": " banana", "price": 2.0}
        ]
        result = find_item(items, "apple pie")
        assert result == {"name": "apple pie", "price": 5.0}
    
    def test_find_item_unicode_name(self) -> None:
        """Test finding item with unicode characters"""
        items = [
            {"name": "café", "price": 3.0},
            {"name": "naïve", "price": 4.0}
        ]
        result = find_item(items, "café")
        assert result == {"name": "café", "price": 3.0}
    
    def test_find_item_numeric_name(self):
        """Test finding item with numeric string name"""
        items = [
            {"name": "123", "price": 1.0},
            {"name": "456", "price": 2.0}
        ]
        result = find_item(items, "123")
        assert result == {"name": "123", "price": 1.0}


class TestFormatReceipt:
    """Test cases for format_receipt function"""
    
    def test_format_receipt_basic(self) -> None:
        """Test basic receipt formatting"""
        result = format_receipt(100.0, "$")
        assert result == "Total due: $100.00"
    
    def test_format_receipt_decimal_values(self):
        """Test receipt formatting with decimal values"""
        result = format_receipt(123.456, "$")
        assert result == "Total due: $123.46"
    
    def test_format_receipt_zero_total(self):
        """Test receipt formatting with zero total"""
        result = format_receipt(0.0, "$")
        assert result == "Total due: $0.00"
    
    def test_format_receipt_negative_total(self) -> None:
        """Test receipt formatting with negative total"""
        result = format_receipt(-50.0, "$")
        assert result == "Total due: $-50.00"
    
    def test_format_receipt_different_currency(self) -> None:
        """Test receipt formatting with different currency symbols"""
        assert format_receipt(100.0, "€") == "Total due: €100.00"
        assert format_receipt(100.0, "£") == "Total due: £100.00"
        assert format_receipt(100.0, "¥") == "Total due: ¥100.00"
    
    def test_format_receipt_currency_code(self):
        """Test receipt formatting with currency code"""
        result = format_receipt(100.0, "USD ")
        assert result == "Total due: USD 100.00"
    
    def test_format_receipt_empty_currency(self):
        """Test receipt formatting with empty currency"""
        result = format_receipt(100.0, "")
        assert result == "Total due: 100.00"
    
    def test_format_receipt_rounding(self) -> None:
        """Test that receipt properly rounds to 2 decimal places"""
        assert format_receipt(99.999, "$") == "Total due: $100.00"
        assert format_receipt(99.994, "$") == "Total due: $99.99"
        assert format_receipt(99.995, "$") == "Total due: $100.00"
    
    def test_format_receipt_very_large_number(self):
        """Test receipt formatting with very large number"""
        result = format_receipt(999999999.99, "$")
        assert result == "Total due: $999999999.99"
    
    def test_format_receipt_very_small_number(self):
        """Test receipt formatting with very small number"""
        result = format_receipt(0.01, "$")
        assert result == "Total due: $0.01"
    
    def test_format_receipt_integer_total(self) -> None:
        """Test receipt formatting when total is integer"""
        result = format_receipt(100, "$")
        assert result == "Total due: $100.00"
    
    def test_format_receipt_single_decimal(self):
        """Test receipt formatting with single decimal place"""
        result = format_receipt(100.5, "$")
        assert result == "Total due: $100.50"


# Integration tests
class TestIntegration:
    """Integration tests combining multiple functions"""
    
    def test_full_workflow(self) -> None:
        """Test a complete workflow: find, process, format"""
        items = [
            {"name": "apple", "price": 1.50, "quantity": 3, "in_stock": True},
            {"name": "banana", "price": 2.00, "quantity": 2, "in_stock": True},
            {"name": "orange", "price": 3.00, "quantity": 1, "in_stock": False}
        ]
        
        # Find an item
        apple = find_item(items, "apple")
        assert apple is not None
        assert apple["name"] == "apple"
        
        # Process items
        total = process_items(items)
        assert total == pytest.approx(8.50)
        
        # Format receipt
        receipt = format_receipt(total, "$")
        assert receipt == "Total due: $8.50"
    
    def test_empty_workflow(self) -> None:
        """Test workflow with empty inventory"""
        items = []
        
        # Find returns None
        result = find_item(items, "apple")
        assert result is None
        
        # Process returns 0.0
        total = process_items(items)
        assert total == 0.0
        
        # Format still works
        receipt = format_receipt(total, "$")
        assert receipt == "Total due: $0.00"