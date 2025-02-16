/*
/// Module: car
module car::car;
*/
module car::car {
    use sui::object::{Self, UID};
    use sui::tx_context::{Self, TxContext};
    use sui::transfer;

    public struct Car has key {
        id: UID,
        speed: u64,
        acceleration: u64,
        handling: u64
    }

    public fun new(speed: u64, acceleration: u64, handling: u64, ctx: &mut TxContext): Car {
        Car { 
            id: object::new(ctx),
            speed: speed,
            acceleration: acceleration,
            handling: handling
        }
    }

    public entry fun create(speed: u64, acceleration: u64, handling: u64, ctx: &mut TxContext) {
        let car = new(speed, acceleration, handling, ctx);
        transfer::transfer(car, tx_context::sender(ctx));
    }

    public entry fun transfer(car: Car, recipient: address) {
        transfer::transfer(car, recipient);
    }

    public fun get_stats(self: &Car): (u64, u64, u64) {
        (self.speed, self.acceleration, self.handling)
    }

    public fun upgrade_speed(self: &mut Car, amount: u64) {
        self.speed = self.speed + amount;
    }


}