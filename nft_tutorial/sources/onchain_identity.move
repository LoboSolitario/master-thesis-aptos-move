module nft_tutorial::onchain_identity {
    
    use std::option::{Self, Option};
    
    use sui::transfer;
    use sui::object::{Self, UID};
    use std::string::{Self, String};
    use sui::tx_context::{Self, TxContext};

    const EProfileMismatch: u64 = 0;

    public struct AdminCap has key {
        id: UID,
    }

    public struct UserProfile has key {
        id: UID,
        name: String,
        user_address: address,
        bio: Option<String>,
        twitter_handle: Option<String>,
    }

    public entry fun create_profile(name: vector<u8>, ctx: &mut TxContext) {
        let user_profile = UserProfile {
            id: object::new(ctx),
            name: string::utf8(name),
            user_address: tx_context::sender(ctx),
            bio: option::none(),
            twitter_handle: option::none(),
        };

        transfer::transfer(user_profile, tx_context::sender(ctx));
    }

    public entry fun change_bio(user_profile: &mut UserProfile, new_bio: vector<u8>, ctx: &mut TxContext) {
        assert!(tx_context::sender(ctx) == user_profile.user_address, EProfileMismatch);
        
        let old_bio = option::swap_or_fill(&mut user_profile.bio, string::utf8(new_bio));


        // old_bio is no longer valid, so we delete it
        _ = old_bio;
    }

    public entry fun delete_profile(_: &AdminCap, user_profile: UserProfile) {
        let UserProfile { 
            id,
            user_address: _,
            name: _,
            bio: _,
            twitter_handle: _,
        } = user_profile;

        object::delete(id);
    }
}