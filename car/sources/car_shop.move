module car::car_shop {

    use sui::transfer;
    use sui::sui::SUI;
    use sui::coin::{Self, Coin};    
    use sui::object::{Self, UID};
    use sui::balance::{Self, Balance};
    use sui::tx_context::{Self, TxContext};

    const EinsufficientBalance: u64 = 0;

    public struct Car has key {
        id: UID,
        speed: u8,
        acceleration: u8,
        handling: u8
    }

    public struct CarShop has key {
        id: UID,
        price: u64,
        balance: Balance<SUI>
    }

    public struct ShopOwnerCap has key {
        id: UID
    }

    fun init(ctx: &mut TxContext) {
        transfer::transfer(ShopOwnerCap {
            id: object::new(ctx)
        }, tx_context::sender(ctx));

        transfer::share_object(CarShop {
            id: object::new(ctx),
            price: 100,
            balance: balance::zero()
        });
    }

    public entry fun buy_car(shop: &mut CarShop, payment: &mut Coin<SUI>, ctx: &mut TxContext) { 
        assert!(coin::value(payment) >= shop.price, EinsufficientBalance);

        let coin_balance = coin::balance_mut(payment);
        let paid = balance::split(coin_balance, shop.price);

        balance::join(&mut shop.balance, paid);

        transfer::transfer(Car {
            id: object::new(ctx  ),
            speed: 100,
            acceleration: 100,
            handling: 100
        }, tx_context::sender(ctx));
    }

    public entry fun collect_profits(_: &ShopOwnerCap, shop: &mut CarShop, ctx: &mut TxContext) {
        let amount = balance::value(&shop.balance);
        let profits = coin::take(&mut shop.balance, amount, ctx);
        transfer::public_transfer(profits, tx_context::sender(ctx));
    }
}