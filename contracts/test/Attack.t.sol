// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {LaunchPool, LaunchToken, LaunchFactory, IERC20} from "../src/DiemLaunch.sol";

interface Vm {
    function createSelectFork(string calldata urlOrAlias) external returns (uint256);
    function prank(address sender) external;
    function startPrank(address sender) external;
    function stopPrank() external;
    function warp(uint256) external;
    function expectRevert(bytes calldata) external;
}

interface IUniV3Factory {
    function createPool(address a, address b, uint24 fee) external returns (address);
}

interface IUniV3Pool {
    function initialize(uint160) external;
    function mint(address, int24, int24, uint128, bytes calldata) external returns (uint256, uint256);
    function token0() external view returns (address);
    function token1() external view returns (address);
}

interface IRouter {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }
    function exactInput(ExactInputParams calldata) external payable returns (uint256);
}

contract AttackTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    IERC20 constant VVV = IERC20(0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf);
    address constant STAKING = 0x321b7ff75154472B18EDb199033fF4D116F340Ff;
    IUniV3Factory constant UNI = IUniV3Factory(0x33128a8fC17869897dcE68Ed026d694621f6FDfD);
    IRouter constant ROUTER = IRouter(0x2626664c2603336E57B271c5C0b26F421741e481);
    uint24 constant FEE = 3000;
    uint160 constant SQRT_1_1 = 79228162514264337593543950336;

    address constant CREATOR = address(0xA11CE);
    address constant BUYER = address(0xB0B);
    address constant ATTACKER = address(0xBADD);

    IUniV3Pool univ3;

    function uniswapV3MintCallback(uint256 a0, uint256 a1, bytes calldata) external {
        require(msg.sender == address(univ3), "bad cb");
        if (a0 > 0) IERC20(univ3.token0()).transfer(msg.sender, a0);
        if (a1 > 0) IERC20(univ3.token1()).transfer(msg.sender, a1);
    }

    function _fund(address to, uint256 amt) internal {
        vm.prank(STAKING);
        VVV.transfer(to, amt);
    }

    function _newPool(uint256 rate, uint256 cap) internal returns (LaunchPool p) {
        p = new LaunchPool(CREATOR, "Serf", "SERF", rate, address(0), cap);
    }

    // ------------------------------------------------------------------
    // ATTACK 1: the fixed mint rate is a hard PRICE CEILING. Any buyback
    // that pushes the market above the peg is free money for an arbitrageur,
    // who mints at peg and dumps. The yield leaks out instead of accruing.
    // ------------------------------------------------------------------
    function testPegArbitrageDrainsBuybackValue() external {
        vm.createSelectFork("base");
        // 1 VVV -> 1 SERF peg, uncapped, sale left OPEN.
        LaunchPool pool = _newPool(1e18, 0);
        LaunchToken serf = pool.token();

        // seed a 1:1 VVV/SERF pool
        _fund(BUYER, 60_000e18);
        vm.startPrank(BUYER);
        VVV.approve(address(pool), 60_000e18);
        pool.buy(60_000e18);
        serf.transfer(address(this), 50_000e18);
        vm.stopPrank();
        _fund(address(this), 50_000e18);

        univ3 = IUniV3Pool(UNI.createPool(address(VVV), address(serf), FEE));
        univ3.initialize(SQRT_1_1);
        univ3.mint(address(this), -887220, 887220, uint128(20_000e18), "");

        // Owner burns 5,000 VVV of treasury yield buying SERF -> price rises.
        _fund(address(pool), 5_000e18);
        bytes memory buyPath = abi.encodePacked(address(VVV), FEE, address(serf));
        vm.prank(CREATOR);
        pool.buybackAndBurn(buyPath, 5_000e18, 1);

        // Arbitrageur: mint at the peg (1 VVV -> 1 SERF), sell into the pumped pool.
        uint256 stake = 5_000e18;
        _fund(ATTACKER, stake);
        vm.startPrank(ATTACKER);
        VVV.approve(address(pool), stake);
        uint256 minted = pool.buy(stake);
        serf.approve(address(ROUTER), minted);
        uint256 vvvBack = ROUTER.exactInput(
            IRouter.ExactInputParams({
                path: abi.encodePacked(address(serf), FEE, address(VVV)),
                recipient: ATTACKER,
                amountIn: minted,
                amountOutMinimum: 0
            })
        );
        vm.stopPrank();

        // DOCUMENTED HAZARD, not a passing grade: while the sale is open at a
        // fixed peg, the peg is a hard price ceiling and buyback value leaks to
        // arbitrageurs. Measured here at ~18.6% of the 5,000 VVV spent.
        require(vvvBack > stake, "no arbitrage available");
        uint256 profit = vvvBack - stake;
        require(profit > stake / 10, "arb smaller than expected - recheck peg model");
    }

    /// Closing the sale removes the arbitrage: minting at peg is no longer possible.
    function testClosedSaleBlocksPegArbitrage() external {
        vm.createSelectFork("base");
        LaunchPool pool = _newPool(1e18, 0);
        _fund(BUYER, 10e18);
        vm.startPrank(BUYER);
        VVV.approve(address(pool), 10e18);
        pool.buy(10e18);
        vm.stopPrank();

        vm.prank(CREATOR);
        pool.setSaleOpen(false);

        _fund(ATTACKER, 10e18);
        vm.startPrank(ATTACKER);
        VVV.approve(address(pool), 10e18);
        vm.expectRevert("SALE_CLOSED");
        pool.buy(10e18);
        vm.stopPrank();
    }

    /// The supply cap bounds dilution even with the sale left open.
    function testSupplyCapEnforced() external {
        vm.createSelectFork("base");
        LaunchPool pool = _newPool(1000e18, 50_000e18); // cap 50k SERF
        _fund(BUYER, 100e18);
        vm.startPrank(BUYER);
        VVV.approve(address(pool), 100e18);
        pool.buy(40e18); // 40k SERF, ok
        vm.expectRevert("CAP_EXCEEDED");
        pool.buy(20e18); // would be 60k total
        vm.stopPrank();
        require(pool.soldSupply() == 40_000e18, "soldSupply wrong");
    }

    // ------------------------------------------------------------------
    // ATTACK 2: ownership. A one-step handoff to a dead address would strand
    // the DIEM treasury permanently.
    // ------------------------------------------------------------------
    function testOwnershipRequiresAcceptance() external {
        vm.createSelectFork("base");
        LaunchPool pool = _newPool(1000e18, 0);

        vm.prank(CREATOR);
        pool.setOwner(address(0xDEAD1)); // "typo"
        require(pool.owner() == CREATOR, "owner changed without acceptance");

        // creator can still cancel and retain control
        vm.prank(CREATOR);
        pool.setOwner(BUYER);
        vm.prank(ATTACKER);
        vm.expectRevert("NOT_PENDING");
        pool.acceptOwnership();

        vm.prank(BUYER);
        pool.acceptOwnership();
        require(pool.owner() == BUYER, "acceptance failed");

        vm.prank(CREATOR);
        vm.expectRevert("NOT_OWNER");
        pool.setSaleOpen(false);
    }

    // ------------------------------------------------------------------
    // ATTACK 3: misc hardening
    // ------------------------------------------------------------------
    function testBuybackRejectsZeroSlippageBound() external {
        vm.createSelectFork("base");
        LaunchPool pool = _newPool(1000e18, 0);
        bytes memory path = abi.encodePacked(address(VVV), FEE, address(pool.token()));
        vm.prank(CREATOR);
        vm.expectRevert("NO_SLIPPAGE_BOUND");
        pool.buybackAndBurn(path, 1e18, 0);
    }

    function testTokenRejectsZeroAddressTransfer() external {
        vm.createSelectFork("base");
        LaunchPool pool = _newPool(1000e18, 0);
        LaunchToken serf = pool.token();
        _fund(BUYER, 10e18);
        vm.startPrank(BUYER);
        VVV.approve(address(pool), 10e18);
        pool.buy(10e18);
        vm.expectRevert("ZERO_DEST");
        serf.transfer(address(0), 1e18);
        vm.stopPrank();
    }

    /// Donated launch tokens must not be miscounted as bought-back supply.
    function testDonatedTokensNotBurnedAsBuyback() external {
        vm.createSelectFork("base");
        LaunchPool pool = _newPool(1e18, 0);
        LaunchToken serf = pool.token();

        _fund(BUYER, 60_000e18);
        vm.startPrank(BUYER);
        VVV.approve(address(pool), 60_000e18);
        pool.buy(60_000e18);
        serf.transfer(address(this), 50_000e18);
        serf.transfer(address(pool), 1_000e18); // donation / griefing
        vm.stopPrank();
        _fund(address(this), 50_000e18);

        univ3 = IUniV3Pool(UNI.createPool(address(VVV), address(serf), FEE));
        univ3.initialize(SQRT_1_1);
        univ3.mint(address(this), -887220, 887220, uint128(20_000e18), "");

        _fund(address(pool), 100e18);
        uint256 donated = serf.balanceOf(address(pool));
        bytes memory path = abi.encodePacked(address(VVV), FEE, address(serf));
        vm.prank(CREATOR);
        uint256 burned = pool.buybackAndBurn(path, 100e18, 1);

        require(burned < donated, "burned amount swallowed the donation");
        require(serf.balanceOf(address(pool)) == donated, "donation was consumed");
    }

    function _u(uint256 v) internal pure returns (string memory) {
        if (v == 0) return "0";
        uint256 j = v; uint256 len;
        while (j != 0) { len++; j /= 10; }
        bytes memory s = new bytes(len);
        while (v != 0) { s[--len] = bytes1(uint8(48 + v % 10)); v /= 10; }
        return string(s);
    }
}
