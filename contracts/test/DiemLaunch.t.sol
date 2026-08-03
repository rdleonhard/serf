// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {LaunchFactory, LaunchPool, LaunchToken, IERC20, IVeniceStaking} from "../src/DiemLaunch.sol";

// Self-contained cheatcode interface (no forge-std dependency).
interface Vm {
    function createSelectFork(string calldata urlOrAlias) external returns (uint256);
    function prank(address sender) external;
    function startPrank(address sender) external;
    function stopPrank() external;
    function label(address account, string calldata newLabel) external;
    function expectRevert(bytes calldata revertData) external;
    function warp(uint256 newTimestamp) external;
}

interface IUniV3Factory {
    function createPool(address tokenA, address tokenB, uint24 fee) external returns (address pool);
}

interface IUniV3Pool {
    function initialize(uint160 sqrtPriceX96) external;
    function mint(address recipient, int24 tickLower, int24 tickUpper, uint128 amount, bytes calldata data)
        external
        returns (uint256 amount0, uint256 amount1);
    function token0() external view returns (address);
    function token1() external view returns (address);
}

contract DiemLaunchForkTest {
    Vm constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    IERC20 constant VVV = IERC20(0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf);
    IVeniceStaking constant STAKING = IVeniceStaking(0x321b7ff75154472B18EDb199033fF4D116F340Ff);
    IERC20 constant DIEM = IERC20(0xF4d97F2da56e8c3098f3a8D538DB630A2606a024);

    address constant BUYER = address(0xB0B);
    address constant CREATOR = address(0xA11CE);

    function testFullFlow() external {
        vm.createSelectFork("base");

        // Fund the buyer with VVV by impersonating the staking contract,
        // which holds users' staked VVV.
        uint256 amount = 100e18;
        require(VVV.balanceOf(address(STAKING)) >= amount, "whale too poor");
        vm.prank(address(STAKING));
        VVV.transfer(BUYER, amount);

        // 0. Platform deploys a launch.
        LaunchFactory factory = new LaunchFactory();
        vm.prank(CREATOR);
        (address poolAddr, address tokenAddr) = factory.createLaunch("Fers", "FERS", 1000e18, address(0), 0);
        LaunchPool pool = LaunchPool(poolAddr);
        LaunchToken token = LaunchToken(tokenAddr);

        // 1. Buyer pays VVV, gets launch tokens; VVV auto-staked to sVVV.
        vm.startPrank(BUYER);
        VVV.approve(poolAddr, amount);
        uint256 tokensOut = pool.buy(amount);
        vm.stopPrank();

        require(tokensOut == 100_000e18, "wrong token amount");
        require(token.balanceOf(BUYER) == 100_000e18, "buyer token balance");
        // 2. Pool holds the (non-transferable) sVVV position.
        uint256 sVVV = STAKING.balanceOf(poolAddr);
        require(sVVV >= amount * 99 / 100, "sVVV not credited");

        // 3. Owner locks sVVV to mint DIEM.
        uint256 quote = STAKING.getDiemAmountOut(sVVV);
        require(quote > 0, "zero diem quote");
        vm.prank(CREATOR);
        uint256 diemOut = pool.lockForDiem(sVVV, quote * 99 / 100);
        require(diemOut >= quote * 99 / 100, "diem below quote");
        require(DIEM.balanceOf(poolAddr) == diemOut, "diem not in pool");

        // 4. Owner collects the DIEM to their own wallet.
        vm.prank(CREATOR);
        pool.collectDiem(CREATOR, diemOut);
        require(DIEM.balanceOf(CREATOR) == diemOut, "diem not collected");
    }

    /// Assert the SPECIFIC revert reason. A bare try/catch would also pass when
    /// the call reverts for an unrelated reason (e.g. no sVVV to lock), which
    /// would prove nothing about access control.
    function testOnlyOwnerGuards() external {
        vm.createSelectFork("base");
        LaunchPool pool = new LaunchPool(CREATOR, "Fers", "FERS", 1000e18, address(0), 0);

        vm.startPrank(BUYER);
        vm.expectRevert("NOT_OWNER");
        pool.lockForDiem(1, 0);
        vm.expectRevert("NOT_OWNER");
        pool.collectDiem(BUYER, 1);
        vm.expectRevert("NOT_OWNER");
        pool.setSaleOpen(false);
        vm.expectRevert("NOT_OWNER");
        pool.setOwner(BUYER);
        vm.stopPrank();
    }

    /// A buy too small to mint a whole token must revert, not silently eat VVV.
    function testDustBuyReverts() external {
        vm.createSelectFork("base");
        LaunchPool pool = new LaunchPool(CREATOR, "Fers", "FERS", 1, address(0), 0);
        vm.prank(address(STAKING));
        VVV.transfer(BUYER, 1e18);

        vm.startPrank(BUYER);
        VVV.approve(address(pool), 1e17);
        vm.expectRevert("DUST");
        pool.buy(1e17);
        vm.stopPrank();
        require(VVV.balanceOf(BUYER) == 1e18, "VVV was taken");
    }

    /// Locking must be incremental, and lockableBalance() must exclude what is
    /// already locked (Venice's balanceOf does not).
    function testIncrementalLockAccounting() external {
        vm.createSelectFork("base");
        LaunchPool pool = new LaunchPool(CREATOR, "Fers", "FERS", 1000e18, address(0), 0);
        vm.prank(address(STAKING));
        VVV.transfer(BUYER, 100e18);
        vm.startPrank(BUYER);
        VVV.approve(address(pool), 100e18);
        pool.buy(100e18);
        vm.stopPrank();

        require(pool.lockableBalance() == 100e18, "lockable wrong pre-lock");
        vm.prank(CREATOR);
        pool.lockForDiem(60e18, 0);
        require(pool.lockableBalance() == 40e18, "lockable did not shrink");
        require(pool.sVVVBalance() == 100e18, "balanceOf should still count locked");

        // over-locking is rejected by the pool before it reaches Venice
        vm.prank(CREATOR);
        vm.expectRevert("EXCEEDS_LOCKABLE");
        pool.lockForDiem(41e18, 0);

        vm.prank(CREATOR);
        pool.lockForDiem(40e18, 0);
        require(pool.lockableBalance() == 0, "lockable should be drained");
    }

    /// compound() must not revert when nothing has accrued, and must be owner-gated
    /// so nobody can divert buyback fuel into permanently-locked principal.
    function testCompoundIsSafeWhenEmptyAndOwnerGated() external {
        vm.createSelectFork("base");
        LaunchPool pool = new LaunchPool(CREATOR, "Fers", "FERS", 1000e18, address(0), 0);
        vm.prank(BUYER);
        vm.expectRevert("NOT_OWNER");
        pool.compound();

        vm.prank(CREATOR);
        require(!pool.compound(), "should report nothing claimed");
    }

    // ---------------- buyback-and-burn (real Uniswap V3 on fork) ----------------

    IUniV3Factory constant UNI_FACTORY = IUniV3Factory(0x33128a8fC17869897dcE68Ed026d694621f6FDfD);
    uint24 constant FEE = 3000;
    uint160 constant SQRT_PRICE_1_1 = 79228162514264337593543950336; // 2^96, price 1:1

    IUniV3Pool univ3;

    /// Uniswap V3 mint callback: pay the pool what it asks for.
    function uniswapV3MintCallback(uint256 amount0Owed, uint256 amount1Owed, bytes calldata) external {
        require(msg.sender == address(univ3), "bad callback caller");
        if (amount0Owed > 0) IERC20(univ3.token0()).transfer(msg.sender, amount0Owed);
        if (amount1Owed > 0) IERC20(univ3.token1()).transfer(msg.sender, amount1Owed);
    }

    function testBuybackAndBurn() external {
        vm.createSelectFork("base");
        LaunchPool pool = new LaunchPool(CREATOR, "Fers", "FERS", 1000e18, address(0), 0);
        LaunchToken fers = pool.token();

        // Buyer converts 200 VVV -> 200k FERS (staked to sVVV inside the pool).
        vm.prank(address(STAKING));
        VVV.transfer(BUYER, 200e18);
        vm.startPrank(BUYER);
        VVV.approve(address(pool), 200e18);
        pool.buy(200e18);
        // hand the test contract FERS + VVV to seed a Uniswap pool
        fers.transfer(address(this), 150_000e18);
        vm.stopPrank();
        vm.prank(address(STAKING));
        VVV.transfer(address(this), 150_000e18);

        // Create + seed a real VVV/FERS Uniswap V3 pool at 1:1, full range.
        univ3 = IUniV3Pool(UNI_FACTORY.createPool(address(VVV), address(fers), FEE));
        univ3.initialize(SQRT_PRICE_1_1);
        univ3.mint(address(this), -887220, 887220, uint128(100_000e18), "");

        // Let REAL staking yield accrue — no hand-transferred stand-in.
        vm.warp(block.timestamp + 30 days);
        uint256 pending = pool.pendingYield();
        require(pending > 0, "no yield accrued over 30 days");
        uint256 claimed = pool.claimYield();
        require(claimed >= pending, "claim delivered less than pending");
        require(VVV.balanceOf(address(pool)) == claimed, "claimed VVV not liquid in pool");

        // Wrong path direction must be rejected.
        bytes memory badPath = abi.encodePacked(address(fers), FEE, address(VVV));
        vm.prank(CREATOR);
        vm.expectRevert("BAD_PATH_ENDS");
        pool.buybackAndBurn(badPath, claimed, 1);

        // Non-owner must be rejected.
        bytes memory path = abi.encodePacked(address(VVV), FEE, address(fers));
        vm.prank(BUYER);
        vm.expectRevert("NOT_OWNER");
        pool.buybackAndBurn(path, claimed, 1);

        // Overspending must fail with a clear reason, not an opaque EVM revert.
        vm.prank(CREATOR);
        vm.expectRevert("INSUFFICIENT_VVV");
        pool.buybackAndBurn(path, claimed + 1e18, 1);

        // The real thing: spend claimed yield on FERS and truly burn it.
        uint256 supplyBefore = fers.totalSupply();
        vm.prank(CREATOR);
        uint256 burned = pool.buybackAndBurn(path, claimed, 1);
        require(burned > 0, "nothing bought back");
        require(fers.totalSupply() == supplyBefore - burned, "totalSupply did not fall");
        require(fers.balanceOf(address(pool)) == 0, "pool still holding unburned FERS");
        require(VVV.balanceOf(address(pool)) == 0, "yield not fully spent");
    }
}
