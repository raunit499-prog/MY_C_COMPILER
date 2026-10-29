export const keywords = [
  ['output','printf'], ['input','scanf'], ['each','for'], ['when','if'],
  ['given','else'], ['until','while'], ['execute','do'], ['choose','switch'],
  ['match','case'], ['otherwise','default'], ['snap','break'],
  ['so_on','continue'], ['provide','return']
];
export const config = '# Fixed vocabulary for My C Compiler Web\n' +
  keywords.map(([alias, standard]) => `${standard} = ${alias}`).join('\n') + '\n';
