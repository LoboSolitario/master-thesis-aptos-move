module car::car_admin {
    use sui::object::{Self, UID};
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};

    public struct AdminCapability has key {
        id: UID,
    }

    public struct Car has key {
        id: UID,
        speed: u8,
        acceleration: u8,
        handling: u8
    }


    fun init(ctx: &mut TxContext) {
        transfer::transfer(AdminCapability { 
            id: object::new(ctx) 
        }, tx_context::sender(ctx));
    }

    fun new(speed: u8, acceleration: u8, handling: u8, ctx: &mut TxContext): Car {
        Car {
            id: object::new(ctx),
            speed,
            acceleration,
            handling
        }
    }
    public entry fun create(_: &AdminCapability, speed: u8, acceleration: u8, handling: u8, ctx: &mut TxContext) {
        let car = new(speed, acceleration, handling, ctx);
        transfer::transfer(car, tx_context::sender(ctx));
    }
}
