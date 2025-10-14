pragma solidity ^0.8.0;
import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";

contract CreditOracle is ChainlinkClient {
    using Chainlink for Chainlink.Request;
    
    address private oracle;
    bytes32 private jobId;
    uint256 private fee;
    
    constructor() {
        setPublicChainlinkToken();
        oracle = 0x...;  // Endereço do nó Chainlink
        jobId = "...";   // ID do job Chainlink
        fee = 0.1 * 10 ** 18; // 0.1 LINK
    }
    
    function requestCreditScore(address user) public returns (bytes32 requestId) {
        Chainlink.Request memory request = buildChainlinkRequest(jobId, address(this), this.fulfill.selector);
        request.add("userId", uint256(uint160(user)));
        return sendChainlinkRequestTo(oracle, request, fee);
    }
    
    function fulfill(bytes32 _requestId, uint256 _creditScore) public recordChainlinkFulfillment(_requestId) {
        // Lógica para atualizar o score de crédito do usuário
    }
}