module nft_tutorial::nft_example {

    //importing modules
    use sui::url::{Self, Url};
    use std::string::{Self, String};
    use sui::object::{Self, UID};
    use sui::transfer;
    use sui::tx_context::{Self, TxContext};

    //create the NFT struct
    public struct NFT has key, store {
        id: UID,
        name: String,
        description: String,
        image_url: Url,
    }

    //create the NFT
    public entry fun mint_to_sender(
        name: vector<u8>,
        description: vector<u8>,
        image_url: vector<u8>,
        ctx: &mut TxContext
    ) {
        let sender = tx_context::sender(ctx);
        let nft = NFT {
            id: object::new(ctx),
            name: string::utf8(name),
            description: string::utf8(description),
            image_url: url::new_unsafe_from_bytes(image_url),
        };

        transfer::transfer(nft, sender);

    }
} 


a = b+c,
