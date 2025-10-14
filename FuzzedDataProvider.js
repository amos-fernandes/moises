const { FuzzedDataProvider } = require('fuzzing-tools');

function fuzzTest(data) {
    const fuzz = new FuzzedDataProvider(data);
    const amount = fuzz.consumeNumber();
    const recipient = fuzz.consumeAddress();

    try {
        token.transfer(recipient, amount);
    } catch (error) {
        // Registrar e analisar erros
    }
}

module.exports = { fuzzTest };