// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// Venice protocol contracts on Base mainnet (chain id 8453):
///   VVV   token:              0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf
///   StakingV2 (= sVVV token): 0x321b7ff75154472B18EDb199033fF4D116F340Ff
///   DIEM  token:              0xf4d97f2da56e8c3098f3a8d538db630a2606a024
///
/// sVVV is NOT transferable, so the pool itself holds the staked position
/// and mints DIEM from inside. DIEM is a normal transferable ERC-20, so the
/// pool owner collects it and stakes it with Venice for API capacity.

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IVeniceStaking {
    function stake(address recipient, uint256 amount) external;
    function mintDiem(uint256 sVVVAmountToLock, uint256 minDiemAmountOut) external;
    function getDiemAmountOut(uint256 sVVVAmountToLock) external view returns (uint256);
    function claimAndStake() external;
    function claim() external;
    function pendingRewards(address account) external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
}

/// Uniswap SwapRouter02 (Base: 0x2626664c2603336E57B271c5C0b26F421741e481).
/// Note: SwapRouter02's ExactInputParams has no deadline field.
interface ISwapRouter02 {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }

    function exactInput(ExactInputParams calldata params) external payable returns (uint256 amountOut);
}

/// FRES: the custom reserve token, minted by its LaunchPool for VVV.
///
/// This is the Juicebox v6 revnet's RESERVE / terminal-accounting token, not its
/// project token. The revnet's project token (SERF) is deployed and minted by JB
/// itself (JBController.deployERC20For), so a reserve token needs only to be a
/// standard ERC-20 the terminal can hold, swap, and pair on Uniswap — no IJBToken
/// interface and no JB mint authority. It therefore has exactly one minter (the
/// pool); JB never mints FRES.
contract LaunchToken {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    address public immutable minter;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(string memory name_, string memory symbol_, address minter_) {
        name = name_;
        symbol = symbol_;
        minter = minter_;
    }

    function mint(address to, uint256 amount) external {
        require(msg.sender == minter, "NOT_MINTER");
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(to != address(0), "ZERO_DEST"); // use burn(); a 0-address transfer
        balanceOf[msg.sender] -= amount; // would look like a burn but leave totalSupply high
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        require(to != address(0), "ZERO_DEST");
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) allowance[from][msg.sender] = allowed - amount;
        balanceOf[from] -= amount;
        balanceOf[to] += amount;
        emit Transfer(from, to, amount);
        return true;
    }

    /// Destroy the caller's own tokens, reducing totalSupply for real (the pool
    /// calls this on bought-back FRES). A transfer to a dead address would leave
    /// totalSupply overstated for explorers and any supply-based math.
    function burn(uint256 amount) external {
        balanceOf[msg.sender] -= amount;
        totalSupply -= amount;
        emit Transfer(msg.sender, address(0), amount);
    }
}

/// Sale pool: VVV in -> launch tokens out; VVV is immediately staked to sVVV;
/// owner locks sVVV to mint DIEM and collects the DIEM.
contract LaunchPool {
    IERC20 public constant VVV = IERC20(0xacfE6019Ed1A7Dc6f7B508C02d1b04ec88cC21bf);
    IVeniceStaking public constant STAKING = IVeniceStaking(0x321b7ff75154472B18EDb199033fF4D116F340Ff);
    IERC20 public constant DIEM = IERC20(0xF4d97F2da56e8c3098f3a8D538DB630A2606a024);
    ISwapRouter02 public constant ROUTER = ISwapRouter02(0x2626664c2603336E57B271c5C0b26F421741e481);
    address public constant DEAD = 0x000000000000000000000000000000000000dEaD;

    LaunchToken public immutable token;
    address public owner;
    uint256 public tokensPerVVV; // launch tokens minted per 1e18 VVV, 1e18-scaled
    bool public saleOpen = true;

    /// One-way switch. An open fixed-rate sale is a hard price ceiling on the
    /// launch token (proven arbitrageable in Attack.t.sol), so before a revnet
    /// or any buyback-driven price support goes live, the sale must be closed
    /// in a way the owner cannot quietly reverse. Once set, buy() is dead and
    /// setSaleOpen() cannot reopen it.
    bool public saleClosedForever;

    /// Venice's sVVV balanceOf() keeps counting sVVV that is already locked into
    /// DIEM, and re-locking it reverts with INSUFFICIENT_BALANCE. There is no
    /// public getter for the locked portion, so the pool tracks it here.
    uint256 public totalLocked;

    /// Hard cap on FRES supply (0 = uncapped). Immutable: a raisable cap is
    /// indistinguishable from no cap. The pool is FRES's only minter and buy()
    /// is its only mint path, so this is a true, total supply ceiling.
    uint256 public immutable maxSaleSupply;
    uint256 public soldSupply;

    /// Two-step ownership. A one-step setOwner to a wrong address would strand
    /// the DIEM treasury forever, since nothing here can be recovered otherwise.
    address public pendingOwner;

    /// STAKING is an upgradeable proxy, so its callbacks are not fully trusted.
    uint256 private _entered = 1;

    modifier nonReentrant() {
        require(_entered == 1, "REENTRANT");
        _entered = 2;
        _;
        _entered = 1;
    }

    event Bought(address indexed buyer, uint256 vvvIn, uint256 tokensOut);
    event OwnershipTransferStarted(address indexed from, address indexed to);
    event DiemMinted(uint256 sVVVLocked, uint256 diemOut);
    event DiemCollected(address indexed to, uint256 amount);
    event YieldClaimed(uint256 vvvAmount);
    event BuybackBurned(uint256 vvvIn, uint256 tokensBurned);
    event SaleClosedForever();
    event SaleOpenSet(bool open);
    event OwnerSet(address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    constructor(
        address owner_,
        string memory name_,
        string memory symbol_,
        uint256 tokensPerVVV_,
        uint256 maxSaleSupply_
    ) {
        require(owner_ != address(0) && tokensPerVVV_ != 0, "BAD_PARAMS");
        owner = owner_;
        tokensPerVVV = tokensPerVVV_;
        maxSaleSupply = maxSaleSupply_;
        token = new LaunchToken(name_, symbol_, address(this));
    }

    /// Pay VVV, receive launch tokens; the VVV is staked to sVVV in the same tx.
    function buy(uint256 vvvAmount) external nonReentrant returns (uint256 tokensOut) {
        require(saleOpen, "SALE_CLOSED");
        require(vvvAmount != 0, "ZERO");
        require(VVV.transferFrom(msg.sender, address(this), vvvAmount), "VVV_IN_FAILED");

        VVV.approve(address(STAKING), vvvAmount);
        STAKING.stake(address(this), vvvAmount);

        tokensOut = (vvvAmount * tokensPerVVV) / 1e18;
        require(tokensOut != 0, "DUST"); // never take VVV and mint nothing
        soldSupply += tokensOut;
        require(maxSaleSupply == 0 || soldSupply <= maxSaleSupply, "CAP_EXCEEDED");
        token.mint(msg.sender, tokensOut);
        emit Bought(msg.sender, vvvAmount, tokensOut);
    }

    /// Lock the pool's not-yet-locked sVVV to mint DIEM. Locking is incremental,
    /// so this can be called again as more buyers arrive. minDiemOut guards the
    /// mint curve; quote it off-chain with STAKING.getDiemAmountOut(sVVVAmount).
    function lockForDiem(uint256 sVVVAmount, uint256 minDiemOut)
        external
        onlyOwner
        nonReentrant
        returns (uint256 diemOut)
    {
        require(sVVVAmount != 0 && sVVVAmount <= lockableBalance(), "EXCEEDS_LOCKABLE");
        uint256 before = DIEM.balanceOf(address(this));
        STAKING.mintDiem(sVVVAmount, minDiemOut);
        diemOut = DIEM.balanceOf(address(this)) - before;
        totalLocked += sVVVAmount;
        emit DiemMinted(sVVVAmount, diemOut);
    }

    /// sVVV that can still be locked. Use THIS, not sVVVBalance(), to size a lock.
    function lockableBalance() public view returns (uint256) {
        uint256 bal = STAKING.balanceOf(address(this));
        return bal > totalLocked ? bal - totalLocked : 0;
    }

    /// PERMISSIONLESS: converge the pool to 100% DIEM. Anyone may call; locking
    /// everything lockable is always the mission, so there is nothing to grief.
    /// minDiemOut is the same-transaction quote: getDiemAmountOut and mintDiem
    /// read identical state, so today this is exact (verified on fork — the
    /// mint pays out precisely the quote). If a Venice upgrade ever breaks that
    /// equality, this fails closed instead of accepting a surprise rate.
    /// Honest limitation: a same-block quote cannot defend against curve
    /// manipulation via DIEM supply changes; it defends against upgrades and
    /// nonlinearity, not MEV. The curve's supply-dependence makes manipulation
    /// capital-expensive (attacker must lock own sVVV), not impossible.
    function lockAll() external nonReentrant returns (uint256 diemOut) {
        uint256 amount = lockableBalance();
        require(amount != 0, "NOTHING_TO_LOCK");
        uint256 quote = STAKING.getDiemAmountOut(amount);
        uint256 before = DIEM.balanceOf(address(this));
        STAKING.mintDiem(amount, quote);
        diemOut = DIEM.balanceOf(address(this)) - before;
        totalLocked += amount;
        emit DiemMinted(amount, diemOut);
    }

    /// Send minted DIEM to the owner's wallet (stake it with Venice for API capacity).
    function collectDiem(address to, uint256 amount) external onlyOwner nonReentrant {
        require(to != address(0), "ZERO_DEST");
        require(DIEM.transfer(to, amount), "DIEM_OUT_FAILED");
        emit DiemCollected(to, amount);
    }

    /// Compound staking rewards back into sVVV.
    /// OWNER ONLY, deliberately: compounding and buybacks draw on the same
    /// yield, and staked principal can never be unstaked here. If this were
    /// public, anyone could front-run every claim and permanently divert 100%
    /// of the buyback fuel into locked principal — a griefing attack on the
    /// tokenomics. The compound/buyback split is monetary policy, not a keeper job.
    /// Venice reverts with STAKE_ZERO when nothing has accrued, so this reports
    /// failure instead of reverting.
    function compound() external onlyOwner returns (bool claimed) {
        try STAKING.claimAndStake() {
            return true;
        } catch {
            return false;
        }
    }

    /// Claim accrued VVV staking yield into the pool WITHOUT restaking it,
    /// making it available for buybacks. Callable by anyone (yield can only
    /// ever land in the pool). Reports zero instead of reverting.
    function claimYield() public returns (uint256 claimed) {
        uint256 before = VVV.balanceOf(address(this));
        try STAKING.claim() {} catch {}
        claimed = VVV.balanceOf(address(this)) - before;
        if (claimed != 0) emit YieldClaimed(claimed);
    }

    /// VVV yield accrued and not yet claimed.
    function pendingYield() external view returns (uint256) {
        return STAKING.pendingRewards(address(this));
    }

    /// Spend the pool's liquid VVV (claimed yield) buying the launch token on
    /// Uniswap V3 and burning it — supply-side value return. `path` is a
    /// standard V3 path that MUST start at VVV and end at the launch token;
    /// output is sent straight to the dead address. Owner quotes minTokensOut
    /// off-chain for slippage/MEV protection.
    function buybackAndBurn(bytes calldata path, uint256 vvvAmount, uint256 minTokensOut)
        external
        onlyOwner
        nonReentrant
        returns (uint256 burned)
    {
        require(minTokensOut != 0, "NO_SLIPPAGE_BOUND"); // 0 = free lunch for MEV
        claimYield();
        (address pathIn, address pathOut) = _pathEnds(path);
        require(pathIn == address(VVV) && pathOut == address(token), "BAD_PATH_ENDS");
        require(vvvAmount != 0 && vvvAmount <= VVV.balanceOf(address(this)), "INSUFFICIENT_VVV");

        VVV.approve(address(ROUTER), vvvAmount);
        // Swap to THIS pool, then burn for real, so totalSupply actually falls.
        uint256 before = token.balanceOf(address(this));
        ROUTER.exactInput(
            ISwapRouter02.ExactInputParams({
                path: path,
                recipient: address(this),
                amountIn: vvvAmount,
                amountOutMinimum: minTokensOut
            })
        );
        burned = token.balanceOf(address(this)) - before;
        token.burn(burned);
        emit BuybackBurned(vvvAmount, burned);
    }

    /// First and last token of a Uniswap V3 path (20-byte addr + 3-byte fee per hop).
    function _pathEnds(bytes calldata path) private pure returns (address first, address last) {
        require(path.length >= 43 && (path.length - 20) % 23 == 0, "BAD_PATH");
        first = address(bytes20(path[:20]));
        last = address(bytes20(path[path.length - 20:]));
    }

    /// Total sVVV held, INCLUDING sVVV already locked into DIEM.
    /// This is NOT what you can lock — use lockableBalance() for that.
    function sVVVBalance() external view returns (uint256) {
        return STAKING.balanceOf(address(this));
    }

    function setSaleOpen(bool open) external onlyOwner {
        require(!saleClosedForever, "CLOSED_FOREVER");
        saleOpen = open;
        emit SaleOpenSet(open);
    }

    /// Irreversibly end the sale. Required sequencing before a revnet (or any
    /// price-support mechanism) goes live: an open fixed-rate sale caps the
    /// token price at the peg and converts price support into arbitrage profit.
    function closeSaleForever() external onlyOwner {
        saleClosedForever = true;
        saleOpen = false;
        emit SaleClosedForever();
        emit SaleOpenSet(false);
    }

    /// Step 1 of 2. The new owner must call acceptOwnership() to take control,
    /// so a typo cannot strand the treasury. Pass address(0) to cancel.
    function setOwner(address newOwner) external onlyOwner {
        pendingOwner = newOwner;
        emit OwnershipTransferStarted(owner, newOwner);
    }

    /// Step 2 of 2, called by the incoming owner. Proves the key is live.
    function acceptOwnership() external {
        require(msg.sender == pendingOwner && msg.sender != address(0), "NOT_PENDING");
        owner = msg.sender;
        pendingOwner = address(0);
        emit OwnerSet(msg.sender);
    }
}

/// Deploys a LaunchPool + LaunchToken pair per launch. This is the "platform".
contract LaunchFactory {
    address[] public pools;

    event LaunchCreated(address indexed pool, address indexed token, address indexed owner, string symbol);

    /// maxSaleSupply_: hard cap on FRES supply, or 0 for uncapped. Fixed forever.
    function createLaunch(
        string calldata name_,
        string calldata symbol_,
        uint256 tokensPerVVV_,
        uint256 maxSaleSupply_
    ) external returns (address pool, address token) {
        LaunchPool p = new LaunchPool(msg.sender, name_, symbol_, tokensPerVVV_, maxSaleSupply_);
        pools.push(address(p));
        emit LaunchCreated(address(p), address(p.token()), msg.sender, symbol_);
        return (address(p), address(p.token()));
    }

    function poolCount() external view returns (uint256) {
        return pools.length;
    }
}
