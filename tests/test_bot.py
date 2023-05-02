import unittest
from unittest.mock import MagicMock, patch
import aiounittest
from app.app import create_order, orders_user, rate_order, review_order, order, conversation, done, order_choice, button, review, help, error_handler

class AwaitableMagicMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

class TestTelegramBot(aiounittest.AsyncTestCase):
    @patch("app.create_order")
    async def test_order(self, mock_create_order):
        update = MagicMock()
        context = MagicMock()

        await order(update, context)

        mock_create_order.assert_called_once_with(str(update.effective_chat.id))
        context.bot.send_message.assert_called_once()

    async def test_conversation(self):
        update = MagicMock()
        context = MagicMock()

        await conversation(update, context)

        context.bot.send_message.assert_called_once()

    @patch("app.orders_user")
    async def test_done(self, mock_orders_user):
        update = MagicMock()
        context = MagicMock()

        # Test with no unrated orders
        mock_orders_user.return_value = []
        await done(update, context)
        update.message.reply_text.assert_called_with("You have no unrated orders. Use the comand '/order' to create a new one")

        # Test with unrated orders
        mock_orders_user.return_value = ["101", "102", "103"]
        await done(update, context)
        update.message.reply_text.assert_called_with("Pick an order to rate:", reply_markup=MagicMock())

    ### I would continue using this pattern of using @patch
    ### to simulate the functions that alter the db directly
    ### Another option is to create a test.db but then I 
    ### think I'd have to adjust all the db functions to take the 
    ### name of the db as a parameter


if __name__ == '__main__':
    unittest.main()
