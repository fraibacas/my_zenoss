
import sys
import os
import subprocess

class FilesCksumRetriever(object):

  EXTENSIONS = [ 'py', 'pt', 'js', 'zcml' ]

  def __init__ (self):
      """ """
      pass

  def _get_cksum(self, full_path_to_file):
      """
      Params: command to execute
      Return: tuple containing the stout and stderr of the command execution
      """
      #print 'Executing ....' + command
      command = 'cksum {0}'.format(full_path_to_file)
      proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      stdout, stderr = proc.communicate()
      cksum = -1
      if len(stderr) == 0:
          cksum = stdout.split()[0]
          if not cksum:
              cksum = -1
      return cksum
 
  def get_files_cksum(self, path):
      """
          Returns a hash with files.
          hash format {file_name} = [ (file_path, cksum), ... ]
      """
      self.path = path
      result = {}
      for root, subFolders, files in os.walk(self.path):
          for f in files:
              extension = f.split('.')[-1]
              if extension in FilesCksumRetriever.EXTENSIONS:
                  full_path = '{0}/{1}'.format(root, f)
                  cksum = self._get_cksum(full_path)
                  partial_path = full_path[len(self.path):]
                  result[partial_path] = cksum
      return result

def find_differences(path1, hash1, path2, hash2):
  """ """
  intersection = [ f for f in hash1.keys() if f in hash2.keys() ]
  files_in_path1_and_not_in_path2 = [ f for f in hash1.keys() if f not in hash2.keys() ]
  files_in_path2_and_not_in_path1 = [ f for f in hash2.keys() if f not in hash1.keys() ]

  different_files = []
  for f in sorted(intersection):
     fc1 = hash1[f]
     fc2 = hash2[f]
     if fc1 != fc2:
         different_files.append(f)
  
  return (files_in_path1_and_not_in_path2, files_in_path2_and_not_in_path1, different_files)


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print 'Error: wrong number of parameters.'
        print 'Usage: files_cksum <path1> <path2>'
    else:
        path1 = sys.argv[1]
        path2 = sys.argv[2]

        cksum_retriever = FilesCksumRetriever()
        print 'Getting checksums from {0}'.format(path1)
        sums1 = cksum_retriever.get_files_cksum(path1)

        print 'Getting checksums from {0}'.format(path2)
        sums2 = cksum_retriever.get_files_cksum(path2)

        (files_in_path1_and_not_in_path2, files_in_path2_and_not_in_path1, different_files) = find_differences(path1, sums1, path2, sums2)

        print '-----------------------------------------------------------------------'
        print 'Files in {0} but not in {1}:'.format(path1, path2)
        print "\n".join(files_in_path1_and_not_in_path2)
        print '-----------------------------------------------------------------------'
        print 'Files in {0} but not in {1}:'.format(path2, path1)
        print "\n".join(files_in_path2_and_not_in_path1)
        print '-----------------------------------------------------------------------'
        print 'Files with different checksum:'
        print "\n".join(different_files)












