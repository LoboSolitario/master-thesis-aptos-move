module address_move::add_benchmark {
    public entry fun add(_account: &signer, a: u64, b: u64) {
        let _sum = a + b;
    }
}