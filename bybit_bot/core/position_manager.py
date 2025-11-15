# core/position_manager.py - COMPLETE WebSocket-Ready Version
from core.risk_manager import safe_float
import streamlit as st
from datetime import datetime
import time

class PositionManager:
    """Position and trade operations management - WebSocket Ready"""
    
    def __init__(self, api_client, logger, database=None, telegram=None, state_manager=None):
        self.api = api_client
        self.logger = logger
        self.database = database
        self.telegram = telegram
        self.state_manager = state_manager  # 🔥 State Manager integration
        
        if 'trade_entries' not in st.session_state:
            st.session_state.trade_entries = {}
        
        if 'open_positions_symbols' not in st.session_state:
            st.session_state.open_positions_symbols = set()
    
    def fetch_and_update_positions(self, symbol=None):
        """
        Fetch positions from API (REST Fallback only)
        در حالت WebSocket این متد فقط برای safety sync استفاده می‌شه
        """
        
        if st.session_state.get('multi_symbol_mode', False) and symbol is None:
            symbols_to_check = st.session_state.get('multi_symbol_list', [])
            if not symbols_to_check:
                symbols_to_check = ['BTCUSDT']
        else:
            symbols_to_check = [symbol] if symbol else ['BTCUSDT']
        
        self.logger.add_log(f"🔄 [FETCH] Checking {len(symbols_to_check)} symbols (REST fallback)", "DEBUG")
        
        all_positions = []
        
        for sym in symbols_to_check:
            try:
                positions_list = self.api.get_positions(sym)
                all_positions.extend(positions_list)
            except Exception as e:
                self.logger.add_log(f"⚠️ [FETCH] Failed to fetch {sym}: {e}", "WARNING")
        
        current_positions = [p for p in all_positions if safe_float(p.get('size')) > 0]
        st.session_state["positions_data"] = current_positions
        
        # 🔥 Sync with state manager
        if self.state_manager:
            self.state_manager.update_positions_from_api(all_positions)
        
        # 🔥 Update portfolio manager
        if 'portfolio_manager' in st.session_state:
            st.session_state.portfolio_manager.update_from_api(all_positions)
        
        current_open_symbols = {p.get('symbol') for p in current_positions}
        closed_symbols = st.session_state.open_positions_symbols - current_open_symbols
        
        if closed_symbols:
            self.logger.add_log(f"🔴 [FETCH] Detected closed: {', '.join(closed_symbols)}", "INFO")
        
        # محاسبه PnL برای positions بسته شده (fallback)
        # در WebSocket این کار در close_position انجام می‌شه
        for symbol_closed in closed_symbols:
            entry_data = st.session_state.trade_entries.get(symbol_closed, {})
            
            if not entry_data:
                continue
            
            # اگه قبلاً save نشده باشه، حالا save کن
            if 'saved_to_db' not in entry_data or not entry_data['saved_to_db']:
                self._save_closed_trade(symbol_closed, entry_data)
        
        st.session_state.open_positions_symbols = current_open_symbols
        
        # Update last prices
        for p in current_positions:
            sym = p.get('symbol')
            
            if sym in st.session_state.trade_entries:
                unrealized = safe_float(p.get('unrealisedPnl', 0))
                mark_price = safe_float(p.get('markPrice', 0))
                st.session_state.trade_entries[sym]['last_unrealized_pnl'] = unrealized
                st.session_state.trade_entries[sym]['last_price'] = mark_price
        
        return current_positions
    
    def _save_closed_trade(self, symbol, entry_data):
        """Helper: ذخیره trade بسته شده"""
        
        entry_price = safe_float(entry_data.get('entry_price'))
        exit_price = safe_float(entry_data.get('exit_price'))
        quantity = safe_float(entry_data.get('quantity'))
        side = entry_data.get('side')
        margin_used = safe_float(entry_data.get('margin_used', 100))
        leverage = entry_data.get('leverage', 1)
        
        if exit_price == 0:
            exit_price = safe_float(entry_data.get('last_price', entry_price))
        
        # محاسبه PnL
        if entry_price > 0 and exit_price > 0 and quantity > 0:
            if side == "Buy":
                pnl_usdt = (exit_price - entry_price) * quantity
            else:
                pnl_usdt = (entry_price - exit_price) * quantity
            
            # کسر کارمزد
            fee_rate = 0.00055
            position_value = quantity * entry_price
            total_fee = position_value * fee_rate * 2
            
            pnl_usdt -= total_fee
            pnl_perc = (pnl_usdt / margin_used * 100) if margin_used > 0 else 0
            
            # ذخیره در database
            if self.database and abs(pnl_usdt) > 0.0001:
                try:
                    trade_data = {
                        'symbol': symbol,
                        'side': side,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'quantity': quantity,
                        'leverage': leverage,
                        'margin_used': margin_used,
                        'pnl_usdt': pnl_usdt,
                        'pnl_percent': pnl_perc,
                        'exit_reason': st.session_state.get('last_exit_reason', 'Unknown'),
                        'entry_time': entry_data.get('entry_time'),
                        'exit_time': entry_data.get('exit_time', datetime.now().isoformat()),
                        'strategy': st.session_state.get('strategy_name', 'Unknown'),
                        'fees': total_fee
                    }
                    
                    self.database.save_trade(trade_data)
                    
                    # بروزرسانی سرمایه
                    current_total_pnl = st.session_state.get("total_realized_pnl", 0.0)
                    st.session_state["total_realized_pnl"] = current_total_pnl + pnl_usdt
                    
                    current_capital = st.session_state.get("current_capital", 0.0)
                    st.session_state["current_capital"] = current_capital + pnl_usdt
                    
                    # Telegram
                    if self.telegram and self.telegram.is_configured():
                        try:
                            self.telegram.notify_exit(
                                symbol=symbol,
                                side=side,
                                entry_price=entry_price,
                                exit_price=exit_price,
                                quantity=quantity,
                                pnl_usdt=pnl_usdt,
                                pnl_percent=pnl_perc,
                                reason=st.session_state.get('last_exit_reason', 'Unknown')
                            )
                        except:
                            pass
                    
                    # Log
                    log_msg = f"💰 **{symbol} CLOSED:** {pnl_usdt:+.2f} USDT ({pnl_perc:+.2f}%)"
                    self.logger.add_log(log_msg, "PNL_UPDATE")
                    
                    # حذف از trade_entries
                    if symbol in st.session_state.trade_entries:
                        del st.session_state.trade_entries[symbol]
                    
                    # Save config
                    from config.settings import ConfigManager
                    ConfigManager.save_config()
                
                except Exception as e:
                    self.logger.add_log(f"❌ Failed to save trade: {e}", "ERROR")
    
    def get_current_position(self, symbol):
        """Get current position status"""
        
        # 🔥 اول از state manager چک کن
        if self.state_manager:
            position = self.state_manager.get_position(symbol)
            if position:
                return position.get('side'), position
        
        # Fallback: از session state
        if st.session_state.get("positions_data") is None:
            self.fetch_and_update_positions(symbol)
        
        positions = st.session_state.get("positions_data", [])
        
        if positions:
            pos = next((p for p in positions 
                       if p.get('symbol') == symbol and safe_float(p.get('size')) > 0), None)
            
            if pos:
                return pos.get("side"), pos
        
        return "None", {}
    
    def close_position(self, symbol, side, size, reason=""):
        """Close position - با immediate save و state sync"""
        if size <= 0:
            return {"retCode": 0, "retMsg": "No position to close"}
        
        exit_time = datetime.now()
        
        self.logger.add_log(f"🔴 [CLOSE] ========== STARTING CLOSE ==========", "INFO")
        self.logger.add_log(f"🔴 [CLOSE] Symbol: {symbol} | Side: {side} | Size: {size:.6f} | Reason: {reason}", "INFO")
        
        # گرفتن قیمت قبل از close
        pre_close_price = 0
        try:
            self.logger.add_log(f"🔍 [CLOSE] Fetching pre-close position...", "DEBUG")
            positions = self.api.get_positions(symbol)
            pre_close_pos = next((p for p in positions if p.get('symbol') == symbol), None)
            
            if pre_close_pos:
                pre_close_price = safe_float(pre_close_pos.get('markPrice'))
                avg_price = safe_float(pre_close_pos.get('avgPrice'))
                self.logger.add_log(
                    f"📊 [CLOSE] Pre-close: Mark={pre_close_price:.4f} | Avg={avg_price:.4f}",
                    "DEBUG"
                )
        except Exception as e:
            self.logger.add_log(f"❌ [CLOSE] Error fetching pre-close: {e}", "ERROR")
        
        # ارسال close order
        self.logger.add_log(f"📤 [CLOSE] Sending close order to API...", "DEBUG")
        result = self.api.close_position(symbol, side, size)
        
        if result.get("retCode") != 0:
            self.logger.add_log(f"❌ [CLOSE] Order failed: {result.get('retMsg')}", "ERROR")
            return result
        
        self.logger.add_log(f"✅ [CLOSE] Order executed successfully", "SUCCESS")
        
        # صبر برای settle
        self.logger.add_log(f"⏳ [CLOSE] Waiting 2 seconds for settlement...", "DEBUG")
        time.sleep(2)
        
        # دریافت exit price واقعی
        actual_exit_price = 0
        
        for attempt in range(3):
            try:
                self.logger.add_log(f"🔍 [CLOSE] Checking position status (attempt {attempt+1}/3)...", "DEBUG")
                
                positions = self.api.get_positions(symbol)
                current_pos = next((p for p in positions if p.get('symbol') == symbol), None)
                
                if current_pos:
                    current_size = safe_float(current_pos.get('size'))
                    
                    if current_size > 0:
                        actual_exit_price = safe_float(current_pos.get('markPrice'))
                        self.logger.add_log(
                            f"⚠️ [CLOSE] Position still open! Size={current_size:.6f}",
                            "WARNING"
                        )
                    else:
                        self.logger.add_log(f"✅ [CLOSE] Position closed completely", "SUCCESS")
                        actual_exit_price = pre_close_price
                        break
                else:
                    self.logger.add_log(f"✅ [CLOSE] Position not found (closed)", "SUCCESS")
                    actual_exit_price = pre_close_price
                    break
                
                time.sleep(1)
            
            except Exception as e:
                self.logger.add_log(f"❌ [CLOSE] Error checking position: {e}", "ERROR")
                time.sleep(1)
        
        # Fallback
        if actual_exit_price == 0:
            actual_exit_price = safe_float(
                st.session_state.trade_entries.get(symbol, {}).get('last_price', 0)
            )
            self.logger.add_log(
                f"⚠️ [CLOSE] Using last_price as fallback: {actual_exit_price:.4f}",
                "WARNING"
            )
        
        if actual_exit_price == 0:
            self.logger.add_log(f"❌ [CLOSE] CRITICAL: Could not determine exit price!", "ERROR")
        
        # 🔥 ذخیره فوری و محاسبه PnL
        if symbol in st.session_state.trade_entries:
            st.session_state.trade_entries[symbol]['exit_price'] = actual_exit_price
            st.session_state.trade_entries[symbol]['exit_time'] = exit_time.isoformat()
            
            self.logger.add_log(
                f"💾 [CLOSE] Saved exit data: Exit={actual_exit_price:.4f}",
                "INFO"
            )
            
            # محاسبه فوری PnL
            entry_data = st.session_state.trade_entries[symbol]
            
            entry_price = safe_float(entry_data.get('entry_price'))
            quantity = safe_float(entry_data.get('quantity'))
            margin_used = safe_float(entry_data.get('margin_used', 100))
            leverage = entry_data.get('leverage', 1)
            
            self.logger.add_log(
                f"📊 [CLOSE] Entry={entry_price:.4f} | Exit={actual_exit_price:.4f} | Qty={quantity:.6f}",
                "DEBUG"
            )
            
            # محاسبه PnL
            if entry_price > 0 and actual_exit_price > 0 and quantity > 0:
                if side == "Buy":
                    pnl_usdt = (actual_exit_price - entry_price) * quantity
                    self.logger.add_log(f"📈 [PNL] Long: ({actual_exit_price:.4f} - {entry_price:.4f}) × {quantity:.6f} = {pnl_usdt:.4f}", "DEBUG")
                else:
                    pnl_usdt = (entry_price - actual_exit_price) * quantity
                    self.logger.add_log(f"📉 [PNL] Short: ({entry_price:.4f} - {actual_exit_price:.4f}) × {quantity:.6f} = {pnl_usdt:.4f}", "DEBUG")
                
                # کسر کارمزد
                fee_rate = 0.00055
                position_value = quantity * entry_price
                total_fee = position_value * fee_rate * 2
                
                self.logger.add_log(f"💸 [PNL] Fees: {total_fee:.4f} USDT", "DEBUG")
                
                pnl_usdt -= total_fee
                pnl_perc = (pnl_usdt / margin_used * 100) if margin_used > 0 else 0
                
                self.logger.add_log(f"💰 [CLOSE] Final PnL: {pnl_usdt:.4f} USDT ({pnl_perc:.2f}%)", "INFO")
                
                # 🔥 ذخیره فوری در database
                if self.database and abs(pnl_usdt) > 0.0001:
                    try:
                        trade_data = {
                            'symbol': symbol,
                            'side': side,
                            'entry_price': entry_price,
                            'exit_price': actual_exit_price,
                            'quantity': quantity,
                            'leverage': leverage,
                            'margin_used': margin_used,
                            'pnl_usdt': pnl_usdt,
                            'pnl_percent': pnl_perc,
                            'exit_reason': reason,
                            'entry_time': entry_data.get('entry_time'),
                            'exit_time': exit_time.isoformat(),
                            'strategy': st.session_state.get('strategy_name', 'Unknown'),
                            'fees': total_fee
                        }
                        
                        self.logger.add_log(f"💾 [CLOSE] Saving trade to database...", "DEBUG")
                        self.database.save_trade(trade_data)
                        self.logger.add_log(f"✅ [CLOSE] Trade saved to database!", "SUCCESS")
                        
                        # بروزرسانی سرمایه
                        current_total_pnl = st.session_state.get("total_realized_pnl", 0.0)
                        st.session_state["total_realized_pnl"] = current_total_pnl + pnl_usdt
                        
                        current_capital = st.session_state.get("current_capital", 0.0)
                        st.session_state["current_capital"] = current_capital + pnl_usdt
                        
                        # Telegram
                        if self.telegram and self.telegram.is_configured():
                            try:
                                self.telegram.notify_exit(
                                    symbol=symbol,
                                    side=side,
                                    entry_price=entry_price,
                                    exit_price=actual_exit_price,
                                    quantity=quantity,
                                    pnl_usdt=pnl_usdt,
                                    pnl_percent=pnl_perc,
                                    reason=reason
                                )
                                self.logger.add_log(f"📱 [TG] Exit notification sent", "DEBUG")
                            except Exception as e:
                                self.logger.add_log(f"⚠️ [TG] Failed: {e}", "WARNING")
                        
                        # Log PnL
                        log_msg = f"💰 **{symbol} CLOSED:** {pnl_usdt:+.2f} USDT ({pnl_perc:+.2f}%)"
                        self.logger.add_log(log_msg, "PNL_UPDATE")
                        
                        # حذف از trade_entries
                        del st.session_state.trade_entries[symbol]
                        self.logger.add_log(f"🗑️ [CLOSE] Removed from trade_entries", "DEBUG")
                        
                        # 🔥 حذف از state manager
                        if self.state_manager:
                            self.state_manager.remove_position(symbol)
                        
                        # حذف از portfolio manager
                        if 'portfolio_manager' in st.session_state:
                            st.session_state.portfolio_manager.remove_position(symbol)
                        
                        # Save config
                        from config.settings import ConfigManager
                        ConfigManager.save_config()
                    
                    except Exception as e:
                        self.logger.add_log(f"❌ [CLOSE] Failed to save trade: {e}", "ERROR")
            
            else:
                self.logger.add_log(
                    f"⚠️ [CLOSE] Invalid data for PnL calculation",
                    "WARNING"
                )
        else:
            self.logger.add_log(f"⚠️ [CLOSE] No trade_entries found for {symbol}!", "WARNING")
        
        st.session_state["last_exit_reason"] = reason
        st.session_state.max_reached_price = 0.0
        st.session_state.min_reached_price = 0.0
        
        self.logger.add_log(f"🔴 [CLOSE] ========== CLOSE COMPLETE ==========", "INFO")
        
        return result
    
    def open_position(self, symbol, side, qty, order_type="Market", price=None, leverage=1):
        """Open new position - با state manager integration"""
        
        # 🔥 چک با state manager
        if self.state_manager:
            can_place, reason = self.state_manager.can_place_order(symbol, side, source="API")
            
            if not can_place:
                self.logger.add_log(f"⛔ [OPEN] Blocked by state manager: {reason}", "WARNING")
                return {"retCode": -1, "retMsg": f"Blocked: {reason}"}
            
            # ثبت pending order
            self.state_manager.register_pending_order(symbol, side, qty, source="API")
        
        entry_time = datetime.now()
        
        self.logger.add_log(f"🟢 [OPEN] ========== STARTING OPEN ==========", "INFO")
        self.logger.add_log(f"🟢 [OPEN] Symbol: {symbol} | Side: {side} | Qty: {qty:.6f} | Leverage: {leverage}x", "INFO")
        
        # ارسال order
        self.logger.add_log(f"📤 [OPEN] Sending order to API...", "DEBUG")
        result = self.api.place_order(symbol, side, qty, order_type, price, leverage)
        
        if result.get("retCode") != 0:
            self.logger.add_log(f"❌ [OPEN] Order failed: {result.get('retMsg')}", "ERROR")
            return result
        
        self.logger.add_log(f"✅ [OPEN] Order placed successfully", "SUCCESS")
        
        # صبر برای settle
        self.logger.add_log(f"⏳ [OPEN] Waiting 2 seconds for settlement...", "DEBUG")
        time.sleep(2)
        
        # دریافت position واقعی
        actual_entry_price = 0
        actual_qty = qty
        
        for attempt in range(3):
            try:
                self.logger.add_log(f"🔍 [OPEN] Fetching position (attempt {attempt+1}/3)...", "DEBUG")
                
                positions = self.api.get_positions(symbol)
                
                self.logger.add_log(f"📊 [OPEN] Received {len(positions)} position(s)", "DEBUG")
                
                current_pos = next((p for p in positions if p.get('symbol') == symbol), None)
                
                if current_pos:
                    actual_entry_price = safe_float(current_pos.get('avgPrice'))
                    actual_qty = safe_float(current_pos.get('size'))
                    pos_side = current_pos.get('side')
                    
                    self.logger.add_log(
                        f"✅ [OPEN] Position found! Side={pos_side} | Entry={actual_entry_price:.4f} | Qty={actual_qty:.6f}",
                        "SUCCESS"
                    )
                    break
                else:
                    self.logger.add_log(f"⚠️ [OPEN] Position not found, retrying...", "WARNING")
                    time.sleep(1)
            
            except Exception as e:
                self.logger.add_log(f"❌ [OPEN] Error fetching position: {e}", "ERROR")
                time.sleep(1)
        
        # بررسی نهایی
        if actual_entry_price == 0:
            self.logger.add_log(f"⚠️ [OPEN] Could not get entry price from API", "ERROR")
            
            if order_type == "Limit" and price:
                actual_entry_price = price
                self.logger.add_log(f"🔄 [OPEN] Using limit price: {actual_entry_price:.4f}", "WARNING")
            else:
                self.logger.add_log(f"❌ [OPEN] CRITICAL: Entry price unknown!", "ERROR")
        
        # محاسبه margin
        if actual_entry_price > 0:
            margin_usdt = (actual_qty * actual_entry_price) / leverage
            self.logger.add_log(f"💰 [OPEN] Margin: {margin_usdt:.2f} USDT", "DEBUG")
        else:
            margin_usdt = st.session_state.get('amount_value', 100.0)
            self.logger.add_log(f"⚠️ [OPEN] Using fallback margin: {margin_usdt:.2f}", "WARNING")
        
        # ذخیره entry data
        entry_data = {
            'entry_time': entry_time.isoformat(),
            'entry_price': actual_entry_price,
            'quantity': actual_qty,
            'margin_used': margin_usdt,
            'leverage': leverage,
            'side': side,
            'exit_price': 0,
            'exit_time': None,
            'last_price': actual_entry_price,
            'last_unrealized_pnl': 0.0,
            'saved_to_db': False
        }
        
        st.session_state.trade_entries[symbol] = entry_data
        st.session_state.open_positions_symbols.add(symbol)
        
        # 🔥 تایید با state manager
        if self.state_manager:
            self.state_manager.confirm_order_filled(symbol, side, actual_entry_price, actual_qty)
        
        # Log
        self.logger.add_log(
            f"💾 [OPEN] Saved: Entry={actual_entry_price:.4f} | Qty={actual_qty:.6f} | Margin={margin_usdt:.2f}",
            "INFO"
        )
        
        # Telegram
        if self.telegram and self.telegram.is_configured():
            try:
                self.telegram.notify_entry(
                    symbol=symbol,
                    side=side,
                    entry_price=actual_entry_price,
                    quantity=actual_qty,
                    leverage=leverage,
                    margin_used=margin_usdt,
                    strategy=st.session_state.get('strategy_name', 'Unknown')
                )
                self.logger.add_log(f"📱 [TG] Entry notification sent", "DEBUG")
            except Exception as e:
                self.logger.add_log(f"⚠️ [TG] Failed: {e}", "WARNING")
        
        self.logger.add_log(f"🟢 [OPEN] ========== OPEN COMPLETE ==========", "INFO")
        
        return result
    
    def set_tp_sl(self, symbol, side, tp_price=None, sl_price=None):
        """Set TP/SL"""
        result = self.api.set_tpsl(symbol, tp_price, sl_price)
        
        if result.get("retCode") == 0:
            self.logger.add_log(f"✅ TP/SL set for {symbol}", "SUCCESS")
        else:
            self.logger.add_log(f"❌ TP/SL failed: {result.get('retMsg')}", "ERROR")
        
        return result
    
    def check_and_adjust_trailing_sl(self, symbol, pos_data, latest_price):
        """Check and adjust Trailing Stop Loss"""
        if not st.session_state.get('use_trailing_sl', False):
            return
        
        # Update last price
        if symbol in st.session_state.trade_entries:
            st.session_state.trade_entries[symbol]['last_price'] = latest_price
        
        side = pos_data.get('side')
        entry_price = safe_float(pos_data.get('avgPrice'))
        current_sl = safe_float(pos_data.get('stopLoss'))
        
        # Get parameters
        trailing_distance_perc = st.session_state.get('trailing_distance_perc', 0.5) / 100
        activation_threshold_perc = st.session_state.get('trailing_activation_perc', 2.0) / 100
        
        # Calculate profit
        if side == "Buy":
            current_profit_perc = ((latest_price - entry_price) / entry_price)
        else:
            current_profit_perc = ((entry_price - latest_price) / entry_price)
        
        # Check activation
        if current_profit_perc < activation_threshold_perc:
            return
        
        # Adjust SL
        if side == "Buy":
            if latest_price > st.session_state.get('max_reached_price', 0.0):
                st.session_state.max_reached_price = latest_price
                from config.settings import ConfigManager
                ConfigManager.save_config()
            
            new_sl = st.session_state.max_reached_price * (1 - trailing_distance_perc)
            
            if current_sl == 0.0:
                sl_perc = st.session_state.get('sl_perc', 0.5)
                current_sl = entry_price * (1 - sl_perc / 100)
            
            if new_sl > current_sl and new_sl > entry_price:
                self.logger.add_log(
                    f"📈 TSL {symbol}: Peak {st.session_state.max_reached_price:.4f} → SL {new_sl:.4f}",
                    "SUCCESS"
                )
                self.api.set_tpsl(symbol, sl_price=new_sl)
        
        elif side == "Sell":
            if st.session_state.get('min_reached_price', 0.0) == 0.0:
                st.session_state.min_reached_price = entry_price
            
            if latest_price < st.session_state.min_reached_price:
                st.session_state.min_reached_price = latest_price
                from config.settings import ConfigManager
                ConfigManager.save_config()
            
            new_sl = st.session_state.min_reached_price * (1 + trailing_distance_perc)
            
            if current_sl == 0.0:
                sl_perc = st.session_state.get('sl_perc', 0.5)
                current_sl = entry_price * (1 + sl_perc / 100)
            
            if new_sl < current_sl and new_sl < entry_price:
                self.logger.add_log(
                    f"📉 TSL {symbol}: Low {st.session_state.min_reached_price:.4f} → SL {new_sl:.4f}",
                    "SUCCESS"
                )
                self.api.set_tpsl(symbol, sl_price=new_sl)