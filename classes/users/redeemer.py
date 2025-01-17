from pytest import approx

from classes.users.user import User

"""
    TODO: Incomplete

    (Add Redeem logic to troves as well)
"""

## Buy Cheap and Redeem if worth more
## If we know the price (of the Collateral) will go up next turn
## Buy cheap now
## Redeem and get more coll
## Coll will be worth more than debt
## Coll -> Debt -> Redeem -> Coll

## TODO: Prob, just like liquidator, you'd loop forever until not profitable
## But you can cap to simulate gas limits
class RedeemArber(User):
    ## TODO: Add data to track self open stuff

    def take_action(self, turn, troves, pool):
        ## They know the next price before it happens
        ## At price set, the pool self-arbs for now TODO: Simulate the universe lmao

        if self.system.total_debt > 0:
            ## Open new position
            self.arb(turn, troves, pool)

    def arb(self, turn, troves, pool):
        # healh check-ups before redeeming
        if len(troves) > 0:
            return

        next_price = self.system.next_price
        price = self.system.price

        ## Specifically, we know that current price is cheaper than next
        ## Meaning we can buy AMT until price goes from current to next
        ## We effectively arb the pool
        ## And do a pure arb, which will pay off next block?

        ## TODO: logic

        # We can buy BTC and redeem it
        if price < next_price:
            ## TODO: Maximize via the LP function
            ## Then interact with Pool and perform the swap
            spot_price = pool.get_price_out(True, 1)

            # Ensure price spot is higher for one unit of collateral, otherwise will
            # not be profitable when consider swap fees and collateral redemp fee
            premium = 1.013  # at least should be ~1.3% in the arb gap
            if spot_price > price * premium:
                print(
                    f"[REDEEMER]Found arb!. System price: {price} and Pool Spot price: {spot_price}"
                )

                prev_coll = self.collateral

                max_coll_in = pool.get_max_coll_before_next_price_sqrt(next_price)

                # Cap if too much
                to_purchase = min(prev_coll, max_coll_in)

                # Value used to cap how much debt we get, never should be more that the total system
                total_system_debt = self.system.total_debt
                # When total system debt is below this magnitude not worthy dealing with dusts
                if total_system_debt < 1e-10:
                    return "NOT WORTHY BEING INVOLVED IN REDEMPTIONS"

                debt_receive = pool.get_price(
                    to_purchase, pool.reserve_x, pool.reserve_y
                )

                if debt_receive > total_system_debt:
                    to_purchase = pool.get_price(
                        total_system_debt, pool.reserve_y, pool.reserve_x
                    )

                # Swap collateral in the pool for debt
                debt_out = pool.swap_for_debt(to_purchase)

                print(f"[REDEEMER]Swapped {to_purchase} in coll for {debt_out} in debt")

                # User Update
                self.collateral -= to_purchase
                self.debt += debt_out

                # Redeem Troves
                redeemed_coll = 0
                for trove in troves:
                    debt_to_redeem = min(trove.debt, self.debt)
                    if debt_to_redeem > 0:
                        redeemed_coll += trove.redeem(debt_to_redeem, self)
                    else:
                        continue

                # After arb we should end-up with zero debt
                assert approx(self.debt) == 0

                # Final Collateral is greater than initial
                assert self.collateral >= prev_coll
                # Final Collateral is equal to initial + total collateral redeemed
                assert (
                    approx(self.collateral) == prev_coll + redeemed_coll - to_purchase
                )
