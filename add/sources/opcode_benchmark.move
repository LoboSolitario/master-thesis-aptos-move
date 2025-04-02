module address_move::opcode_benchmark {
    use std::signer;
    use std::vector;

    struct Storage has key {
        value: u64,
        vec: vector<u64>,
    }

    // Add struct for unpack_ref benchmark
    struct UnpackStruct has key, store, copy, drop {
        f: u64,
        g: u64
    }

    // Add cast counter storage to track operations
    struct CastStorage has key {
        u8_cast_result: u8,
        u16_cast_result: u16,
        u32_cast_result: u32,
        u64_cast_result: u64,
        u128_cast_result: u128,
        u256_cast_result: u256
    }

    // Storage for boolean and constant literals
    struct LiteralStorage has key {
        false_val: bool,
        true_val: bool
    }

    // Generic struct for testing generic operations
    struct GenericStruct<T: store + drop> has key, store, drop {
        value: T
    }

    // Initialize storage for benchmarking
    public entry fun initialize(account: &signer) {
        let addr = signer::address_of(account);
        
        if (!exists<Storage>(addr)) {
            move_to(account, Storage {
                value: 0,
                vec: vector::empty(),
            });
        };
        
        if (!exists<CastStorage>(addr)) {
            move_to(account, CastStorage {
                u8_cast_result: 0,
                u16_cast_result: 0,
                u32_cast_result: 0,
                u64_cast_result: 0,
                u128_cast_result: 0,
                u256_cast_result: 0
            });
        };
        
        if (!exists<LiteralStorage>(addr)) {
            move_to(account, LiteralStorage {
                false_val: false,  // ld_false opcode
                true_val: true    // ld_true opcode
            });
        };
        
        if (!exists<UnpackStruct>(addr)) {
            move_to(account, UnpackStruct {
                f: 42,
                g: 84
            });
        }
    }

    // Arithmetic Operations Benchmark
    public entry fun benchmark_arithmetic(_account: &signer, a: u64, b: u64) {

        // Addition
        let _c = a + b;
        // Subtraction
        let _d = b - a;
        // Multiplication
        let _e = a * b;
        // Division
        let _f = b / a;
        // Modulus
        let _g = b % a;
    }
    // Vector Operations Benchmark
    public entry fun benchmark_vector_ops(_account: &signer) {
        let vec = vector::empty<u64>();
        
        // Push
        vector::push_back(&mut vec, 1);
        vector::push_back(&mut vec, 2);
        vector::push_back(&mut vec, 3);
        
        // Pop
        let _val = vector::pop_back(&mut vec);
        
        // Length
        let _len = vector::length(&vec);
        
        // Borrow
        let _elem = vector::borrow(&vec, 0);
    }

    // Storage Operations Benchmark
    public entry fun benchmark_storage_ops(_account: &signer) acquires Storage {
        let addr = signer::address_of(_account);
        
        // First check if the resource exists to avoid the error
        if (!exists<Storage>(addr)) {
            // If it doesn't exist, create it first
            move_to(_account, Storage {
                value: 0,
                vec: vector::empty(),
            });
        };
        
        // Read from global storage
        let storage = borrow_global_mut<Storage>(addr);
        
        // Write to storage
        storage.value = storage.value + 1;
        
        // Vector operations in storage
        vector::push_back(&mut storage.vec, storage.value);
    }

    // Control Flow Benchmark
    public entry fun benchmark_control_flow(_account: &signer) {
        let _i = 0;
        
        // While loop
        while (_i < 5) {
            _i = _i + 1;
        };
        
        // If-else
        if (_i > 3) {
            _i = _i - 1;
        } else {
            _i = _i + 1;
        };
    }

    // Advanced Arithmetic & Logic Operations Benchmark
    public entry fun benchmark_conditional_logic(_account: &signer, a: u64, b: u64, c: u8, d: u8, bool1: bool, bool2: bool) {
        
        // Greater than or equal (ge)
        let _ge_result = a >= b;
        
        // Less than or equal (le)
        let _le_result = a <= b;
        
        // Not equal (neq)
        let _neq_result = a != b;
        
        // Equal (eq)
        let _eq_result = a == b;
        
        // Not (not)
        let _not_result = !bool1;
        
        // And (and)
        let _and_result = bool1 && bool2;
        
        // Or (or)
        let _or_result = bool1 || bool2;
        
        // Xor (xor)
        let _xor_result = (bool1 != bool2);
        
        // Bit operations work on integer types
        // Bit and (bit_and)
        let _bit_and_result = c & d;
        
        // Bit or (bit_or)
        let _bit_or_result = c | d;
        
        // Bit xor (bit_xor)
        let _bit_xor_result = c ^ d;
    }
    
    // Benchmark bit shift operations
    public entry fun benchmark_bit_shift(_account: &signer, a: u8, b: u8) {
        // Shift left (<<)
        let _shift_left = a << 2;
        let _shift_left_var = a << b;
        
        // Shift right (>>)
        let _shift_right = a >> 2;
        let _shift_right_var = a >> b;
    }

    // Benchmark integer casting operations
    public entry fun benchmark_casting(_account: &signer, in_u8: u8, in_u16: u16, in_u32: u32, in_u64: u64, in_u128: u128, in_u256: u256) {
        // Store input values in local variables to ensure loading operations
        let a_u8: u8 = in_u8;
        let a_u16: u16 = in_u16;
        let a_u32: u32 = in_u32;
        let a_u64: u64 = in_u64;
        let a_u128: u128 = in_u128;
        let a_u256: u256 = in_u256;
        
        // Cast u8 to other types
        let _u8_to_u16 = (a_u8 as u16);
        let _u8_to_u32 = (a_u8 as u32);
        let _u8_to_u64 = (a_u8 as u64);
        let _u8_to_u128 = (a_u8 as u128);
        let _u8_to_u256 = (a_u8 as u256);
        
        // Cast u16 to other types
        let _u16_to_u8 = ((a_u16 % 256) as u8); // Apply modulo to prevent abort
        let _u16_to_u32 = (a_u16 as u32);
        let _u16_to_u64 = (a_u16 as u64);
        let _u16_to_u128 = (a_u16 as u128);
        let _u16_to_u256 = (a_u16 as u256);
        
        // Cast u32 to other types
        let _u32_to_u8 = ((a_u32 % 256) as u8); // Ensure no abort
        let _u32_to_u16 = ((a_u32 % 65536) as u16); // Ensure no abort
        let _u32_to_u64 = (a_u32 as u64);
        let _u32_to_u128 = (a_u32 as u128);
        let _u32_to_u256 = (a_u32 as u256);
        
        // Cast u64 to other types
        let _u64_to_u8 = ((a_u64 % 256) as u8); // Ensure no abort
        let _u64_to_u16 = ((a_u64 % 65536) as u16); // Ensure no abort
        let _u64_to_u32 = ((a_u64 % 4294967296) as u32); // Ensure no abort
        let _u64_to_u128 = (a_u64 as u128);
        let _u64_to_u256 = (a_u64 as u256);
        
        // Cast u128 to other types
        let _u128_to_u8 = ((a_u128 % 256) as u8); // Ensure no abort
        let _u128_to_u16 = ((a_u128 % 65536) as u16); // Ensure no abort
        let _u128_to_u32 = ((a_u128 % 4294967296) as u32); // Ensure no abort
        let _u128_to_u64 = ((a_u128 % 18446744073709551616) as u64); // Ensure no abort
        let _u128_to_u256 = (a_u128 as u256);
        
        // Cast u256 to other types
        let _u256_to_u8 = ((a_u256 % 256) as u8); // Ensure no abort
        let _u256_to_u16 = ((a_u256 % 65536) as u16); // Ensure no abort
        let _u256_to_u32 = ((a_u256 % 4294967296) as u32); // Ensure no abort
        let _u256_to_u64 = ((a_u256 % 18446744073709551616) as u64); // Ensure no abort
        let _u256_to_u128 = ((a_u256 % 340282366920938463463374607431768211456) as u128); // Ensure no abort
        
        // Create and load variables of different types separately to benchmark ld operations
        let b_u8: u8 = 42;
        let b_u16: u16 = 4242;
        let b_u32: u32 = 424242;
        let b_u64: u64 = 42424242;
        let b_u128: u128 = 4242424242;
        let b_u256: u256 = 424242424242;
        
        // Load operations (these will be captured as ld_u* operations)
        let _load_u8 = b_u8;
        let _load_u16 = b_u16;
        let _load_u32 = b_u32;
        let _load_u64 = b_u64;
        let _load_u128 = b_u128;
        let _load_u256 = b_u256;
    }

    // Benchmark for unpack_ref opcode
    public entry fun benchmark_unpack_ref(_account: &signer) {
        // Create a struct instance
        let s = UnpackStruct { f: 100, g: 200 };
        
        // Get a reference to the struct
        let s_ref = &s;
        
        // Unpack the reference using pattern matching - this will use the unpack_ref opcode
        let UnpackStruct { f, g } = s_ref;
        
        // Dereference the fields to ensure values are used
        let _f_val = *f;
        let _g_val = *g;
        
        // Perform the unpack_ref operation multiple times to make it visible in benchmarks
        for (_i in 0..10) {
            let UnpackStruct { f: f2, g: g2 } = s_ref;
            let _sum = *f2 + *g2;
        };
    }
    
    // Benchmark for unpack_ref with global storage
    public entry fun benchmark_unpack_ref_global(account: &signer) acquires UnpackStruct {
        let addr = signer::address_of(account);
        
        // First check if the resource exists to avoid the error
        if (!exists<UnpackStruct>(addr)) {
            // If it doesn't exist, create it first
            move_to(account, UnpackStruct {
                f: 42,
                g: 84
            });
        };
        
        // Get a reference to the struct from global storage
        let s_ref = borrow_global<UnpackStruct>(addr);
        
        // Unpack the reference using pattern matching
        let UnpackStruct { f, g } = s_ref;
        
        // Dereference the fields to ensure values are used
        let _f_val = *f;
        let _g_val = *g;
        
        // Perform the unpack_ref operation multiple times to make it visible in benchmarks
        for (_i in 0..10) {
            let s_ref = borrow_global<UnpackStruct>(addr);
            let UnpackStruct { f: f2, g: g2 } = s_ref;
            let _sum = *f2 + *g2;
        };
    }

    // Benchmark for exists opcode
    public entry fun benchmark_exists(account: &signer) {
        let addr = signer::address_of(account);
        
        // Check if resources exist - uses 'exists' opcode
        let _storage_exists = exists<Storage>(addr);
        let _unpack_struct_exists = exists<UnpackStruct>(addr);
        let _cast_storage_exists = exists<CastStorage>(addr);
        let _literal_storage_exists = exists<LiteralStorage>(addr);
        
        // Use exists in a control flow to ensure the code is actually executed
        if (exists<Storage>(addr)) {
            // Do something trivial
            let _dummy = 1 + 1;
        };
    }
    
    // Benchmark for move_to opcode
    public entry fun benchmark_move_to(account: &signer) {
        let addr = signer::address_of(account);
        
        // Only perform move_to if the resource doesn't already exist
        if (!exists<GenericStruct<u64>>(addr)) {
            // Create a new struct and move it to account's storage
            let generic_struct = GenericStruct<u64> { value: 100 };
            move_to(account, generic_struct); // move_to opcode
        }
    }
    
    // Benchmark for move_from and move_from_generic opcodes
    public entry fun benchmark_move_from(account: &signer) acquires GenericStruct {
        let addr = signer::address_of(account);
        
        // First ensure the resource exists
        if (!exists<GenericStruct<u64>>(addr)) {
            move_to(account, GenericStruct<u64> { value: 100 });
        };
        
        // Move the resource from global storage - uses move_from_generic opcode
        let generic_struct = move_from<GenericStruct<u64>>(addr);
        
        // Use the resource
        let _value = generic_struct.value;
        
        // Move it back to maintain state for future benchmarks
        move_to(account, generic_struct);
    }
    
    // Benchmark for imm_borrow_field_generic opcode
    public entry fun benchmark_imm_borrow_field_generic() {
        // Create a struct instance
        let generic_struct = GenericStruct<u64> { value: 200 };
        
        // Immutably borrow a field from the struct - uses imm_borrow_field_generic
        let value_ref = &generic_struct.value;
        
        // Use the reference
        let _value = *value_ref;
        
        // Use the struct to avoid the drop issue
        let _original_value = generic_struct.value;
    }
    
    // Benchmark for mut_borrow_field_generic opcode
    public entry fun benchmark_mut_borrow_field_generic() {
        // Create a struct instance
        let generic_struct = GenericStruct<u64> { value: 300 };
        
        // Mutably borrow a field from the struct - uses mut_borrow_field_generic
        let value_ref = &mut generic_struct.value;
        
        // Modify the field through the reference
        *value_ref = *value_ref + 1;
        
        // Use the modified struct - no longer a borrowing issue because we added drop
        let _value = generic_struct.value;
    }
    
    // Benchmark for imm_borrow_global_generic opcode
    public entry fun benchmark_imm_borrow_global_generic(account: &signer) acquires GenericStruct {
        let addr = signer::address_of(account);
        
        // Ensure the resource exists
        if (!exists<GenericStruct<u64>>(addr)) {
            move_to(account, GenericStruct<u64> { value: 400 });
        };
        
        // Immutably borrow the resource from global storage - uses imm_borrow_global_generic
        let generic_struct_ref = borrow_global<GenericStruct<u64>>(addr);
        
        // Use the reference
        let _value = generic_struct_ref.value;
    }
    
    // Benchmark for mut_borrow_global_generic opcode
    public entry fun benchmark_mut_borrow_global_generic(account: &signer) acquires GenericStruct {
        let addr = signer::address_of(account);
        
        // Ensure the resource exists
        if (!exists<GenericStruct<u64>>(addr)) {
            move_to(account, GenericStruct<u64> { value: 500 });
        };
        
        // Mutably borrow the resource from global storage - uses mut_borrow_global_generic
        let generic_struct_ref = borrow_global_mut<GenericStruct<u64>>(addr);
        
        // Modify the resource through the reference
        generic_struct_ref.value = generic_struct_ref.value + 1;
    }
    
    // Benchmark for pack_generic opcode
    public entry fun benchmark_pack_generic() {
        // Create instances of the generic struct with different types
        // Each creation uses the pack_generic opcode
        // Now with drop ability, these can be implicitly dropped
        let _generic_u64 = GenericStruct<u64> { value: 600 };
        let _generic_u128 = GenericStruct<u128> { value: 600u128 };
        let _generic_bool = GenericStruct<bool> { value: true };
    }
    
    // Benchmark for unpack opcode
    public entry fun benchmark_unpack() {
        // Create a struct
        let unpack_struct = UnpackStruct { f: 700, g: 800 };
        
        // Destructure the struct using pattern matching - uses unpack opcode
        let UnpackStruct { f, g } = unpack_struct;
        
        // Use the unpacked values
        let _sum = f + g;
    }
    
    // Benchmark for unpack_generic opcode
    public entry fun benchmark_unpack_generic() {
        // Create a generic struct
        let generic_struct = GenericStruct<u64> { value: 900 };
        
        // Destructure the generic struct - uses unpack_generic opcode
        let GenericStruct { value } = generic_struct;
        
        // Use the unpacked value
        let _value_plus_one = value + 1;
    }
} 