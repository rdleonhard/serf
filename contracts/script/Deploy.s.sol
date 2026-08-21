// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {LaunchFactory} from "../src/DiemLaunch.sol";

/// Minimal cheatcode surface, matching the convention in test/ — this project
/// deliberately carries no forge-std dependency.
interface Vm {
    function startBroadcast() external;
    function stopBroadcast() external;
    function envOr(string calldata key, string calldata dflt) external view returns (string memory);
    function envOr(string calldata key, uint256 dflt) external view returns (uint256);
    function envOr(string calldata key, address dflt) external view returns (address);
}

/// Deploy the factory and one launch pool.
///
/// The same script runs against a local Base fork and against Base mainnet on
/// purpose: a deploy path exercised for the first time on the day it matters
/// is not a tested deploy path.
///
///   anvil --fork-url https://mainnet.base.org
///   forge script script/Deploy.s.sol:Deploy \
///     --rpc-url http://127.0.0.1:8545 --broadcast --private-key <anvil key>
///
/// Every value below is immutable once deployed. EXTRA_MINTER especially: any
/// non-zero address is a second mint authority that can mint straight past
/// MAX_SALE_SUPPLY, which makes the cap decorative.
contract Deploy {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    function run() external returns (address factory, address pool, address token) {
        string memory name_ = vm.envOr("TOKEN_NAME", string("Fers"));
        string memory symbol_ = vm.envOr("TOKEN_SYMBOL", string("FERS"));
        uint256 rate = vm.envOr("TOKENS_PER_VVV", uint256(1000e18));
        uint256 cap = vm.envOr("MAX_SALE_SUPPLY", uint256(10_000_000e18));

        vm.startBroadcast();
        LaunchFactory f = new LaunchFactory();
        (pool, token) = f.createLaunch(name_, symbol_, rate, cap);
        vm.stopBroadcast();

        factory = address(f);
    }
}
